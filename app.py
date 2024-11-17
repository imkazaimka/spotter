from flask import Flask, render_template, request, redirect, url_for, session , flash
from models import db, Spot, User, Review, Booking
from authlib.integrations.flask_client import OAuth
from datetime import datetime , timedelta
from calculations import calculate_distance
from weather import get_14_day_forecast , check_rain_or_snow_for_day

import os

app = Flask(__name__)


app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'supersecretkey')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///spotter.db'  # Update with your DB URI
db.init_app(app)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']  # Get the username from the form
        password = request.form['password']  # Get the password from the form
        
        # Find user by username
        user = User.query.filter_by(username=username).first()

        if user and user.password == password:  # Compare passwords directly (plain text)
            session['user_id'] = user.id  # Store user ID in session
            flash("Login successful!", "success")
            return redirect(url_for('home'))  # Redirect to home or any protected page
        else:
            flash("Invalid credentials. Please try again.", "danger")
            return redirect(url_for('login'))  # Redirect to login if invalid credentials

    return render_template('login.html')  # Render the login form




@app.route('/logout')
def logout():
    session.clear()  # Clear the session data to log out
    flash("You have been logged out.", "success")
    return redirect(url_for('home'))  # Redirect to home after logout




# Register
from werkzeug.security import generate_password_hash  # For hashing passwords

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        if not username or not email or not password:
            flash("Missing form data", "danger")
            return redirect(url_for('register'))

        # Check if the user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Email is already in use.", "danger")
            return redirect(url_for('register'))

        # If username is 'admin', set them as admin
        is_admin = username == 'admin' and password == 'admin123'

        # Hash the password before storing it
        hashed_password = generate_password_hash(password)

        # Create a new user instance
        new_user = User(
            username=username,
            email=email,
            password=hashed_password,
            is_admin=is_admin
        )
        db.session.add(new_user)
        db.session.commit()
        
        flash("Registration successful! Please log in.", "success")
        return redirect(url_for('login'))  # Redirect to login after successful registration

    return render_template('register.html')  # Render the registration form








"""
ALL ROOTES FOR /SPOT FROM HERE ON


/spots : show all spots/filter based on location and features

/spots/<int:spot_id> : Full page of a specific spot_id

/spots/<int:spot_id>/add-booking : adds a booking on this spot

/spots/add (Admin user requied) : adds a spot

/spots/<int:spot_id>/edit (admin user required) : edits a spot

"""



@app.route('/spots', methods=['GET'])
def all_spots():
    # Default values
    sort_by = 'name'
    order = 'asc'

    # User location and distance range
    user_lat = request.args.get('lat', type=float)
    user_lon = request.args.get('lon', type=float)
    distance_range = request.args.get('distance_range', type=float)

    # Selected activities
    selected_activities = request.args.getlist('activities')

    # Query spots
    spots = Spot.query.all()

    # Apply sorting
    valid_columns = ['name', 'longitude', 'latitude', 'booking_required', 'car_park', 'outdoor',
                     'hiking', 'biking', 'fishing', 'camping', 'climbing', 'kayaking', 'swimming', 
                     'picnic_area', 'wildlife_watching', 'photography', 'bbq', 'campsite', 'distance']

    sort_by = request.args.get('sort_by', sort_by)
    order = request.args.get('order', order)

    filtered_spots = []
    for spot in spots:
        # Calculate distance from user location if provided
        distance = None
        if user_lat is not None and user_lon is not None:
            distance = calculate_distance(user_lat, user_lon, spot.latitude, spot.longitude)

        # Check if within the distance range
        if distance_range and distance is not None and distance > distance_range:
            continue  # Skip if out of range

        # Check activity filters
        if selected_activities:
            has_selected_activities = any(getattr(spot, activity) for activity in selected_activities)
            if not has_selected_activities:
                continue  # Skip if no matching activities
        
        # Calculate average rating
        reviews = Review.query.filter_by(spot_id=spot.id).all()
        avg_rating = None
        if reviews:
            avg_rating = sum(review.rating for review in reviews) / len(reviews)

        filtered_spots.append({
            'spot': spot,
            'avg_rating': avg_rating,
            'distance': round(distance, 2) if distance is not None else None
        })

     # Sort by distance if specified
    if sort_by == 'distance' and user_lat is not None and user_lon is not None:
        filtered_spots.sort(key=lambda x: x['distance'] if x['distance'] is not None else float('inf'), 
                            reverse=(order == 'desc'))
    elif sort_by in valid_columns:
        sort_column = getattr(Spot, sort_by)
        if order == 'desc':
            spots = Spot.query.order_by(sort_column.desc()).all()
        else:
            spots = Spot.query.order_by(sort_column.asc()).all()

    return render_template(
        'spots.html', 
        spots_with_avg_reviews=filtered_spots, 
        selected_activities=selected_activities,
        user_lat=user_lat,
        user_lon=user_lon,
        distance_range=distance_range
    )




@app.route('/spots/<int:spot_id>', methods=['GET', 'POST'])
def spot_by_id(spot_id):
    # Fetch the spot by its ID
    spot = Spot.query.get(spot_id)
    if not spot:
        return render_template('404.html', message="Spot not found"), 404

    # Fetch all reviews for this spot
    reviews = Review.query.filter_by(spot_id=spot_id).all()
    bookings = Booking.query.filter_by(spot_id=spot.id).all()

    # Filter to show only future bookings (where the start time is in the future)
    future_bookings = [booking for booking in bookings if booking.start_time > datetime.utcnow()]

    # Fetch user information for future bookings
    booked_users = []
    for booking in future_bookings:
        user = User.query.get(booking.user_id)
        booked_users.append({
            'user': user,
            'start_time': booking.start_time,
            'end_time': booking.end_time
        })

    # Calculate average rating for this spot
    avg_rating = None
    if reviews:
        avg_rating = sum(review.rating for review in reviews) / len(reviews)

    # Handle review form submission
    if 'user_id' in session and request.method == 'POST':
        rating = request.form.get('rating')
        comment = request.form.get('comment')

        if rating and comment:
            new_review = Review(
                spot_id=spot_id,
                user_id=session['user_id'],
                rating=int(rating),
                comment=comment
            )
            db.session.add(new_review)
            db.session.commit()
            return redirect(url_for('spot_by_id', spot_id=spot_id))  # Redirect to avoid form resubmission

    # Get 14-day weather forecast for the spot (latitude, longitude)
    weather_forecast = get_14_day_forecast(spot.latitude, spot.longitude)

    # Render the template without weather forecasting information for bookings, but with 14-day forecast
    return render_template(
        'spot_details.html', 
        spot=spot, 
        reviews=reviews, 
        booked_users=booked_users,
        future_bookings=future_bookings,
        avg_rating=avg_rating,
        weather_forecast=weather_forecast  # Pass the 14-day weather forecast to the template
    )









@app.route('/spots/<int:spot_id>/add-booking', methods=['GET', 'POST'])
def add_booking(spot_id):
    spot = Spot.query.get(spot_id)
    if not spot:
        return render_template('404.html', message="Spot not found"), 404

    if request.method == 'POST':
        if 'user_id' not in session:
            # Redirect to login if the user is not logged in
            return redirect(url_for('login', next=request.url))

        start_time = request.form['start_time']
        end_time = request.form['end_time']

        # Convert the start and end times from string to datetime
        start_time = datetime.strptime(start_time, '%Y-%m-%dT%H:%M')
        end_time = datetime.strptime(end_time, '%Y-%m-%dT%H:%M')

        # Create a new booking record
        booking = Booking(
            spot_id=spot_id,
            user_id=session['user_id'],
            start_time=start_time,
            end_time=end_time
        )

        db.session.add(booking)
        db.session.commit()

        # After booking, redirect to the spot details page
        return redirect(url_for('spot_by_id', spot_id=spot_id))

    return render_template('add_booking.html', spot=spot)






@app.route('/spots/add', methods=['GET', 'POST'])
def add_spot():
    # Check if the user is logged in and is an admin
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Redirect to login page if not logged in

    user = User.query.get(session['user_id'])
    if not user or not user.is_admin:
        return "You must be an admin to add spots.", 403  # Only allow admins

    # Handle the form submission
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name')
        description = request.form.get('description')
        longitude = request.form.get('longitude', type=float)
        latitude = request.form.get('latitude', type=float)
        booking_required = request.form.get('booking_required', type=bool)
        car_park = request.form.get('car_park', type=bool)
        outdoor = request.form.get('outdoor', type=bool)
        hiking = request.form.get('hiking', type=bool)
        biking = request.form.get('biking', type=bool)
        fishing = request.form.get('fishing', type=bool)
        camping = request.form.get('camping', type=bool)
        climbing = request.form.get('climbing', type=bool)
        kayaking = request.form.get('kayaking', type=bool)
        swimming = request.form.get('swimming', type=bool)
        picnic_area = request.form.get('picnic_area', type=bool)
        wildlife_watching = request.form.get('wildlife_watching', type=bool)
        photography = request.form.get('photography', type=bool)
        bbq = request.form.get('bbq', type=bool)
        campsite = request.form.get('campsite', type=bool)

        # Validate Latitude and Longitude
        if not (-90 <= latitude <= 90):
            return render_template('add_spot.html', error="Invalid Latitude. It must be between -90 and 90.")
        if not (-180 <= longitude <= 180):
            return render_template('add_spot.html', error="Invalid Longitude. It must be between -180 and 180.")

        # OSM Specific Precision Check: Ensure at least 5 decimal places
        if not validate_osm_coordinates(latitude, longitude):
            return render_template('add_spot.html', error="Coordinates must have at least 5 decimal places for accuracy.")

        # Create new Spot instance
        new_spot = Spot(
            name=name,
            description=description,
            longitude=longitude,
            latitude=latitude,
            booking_required=booking_required,
            car_park=car_park,
            outdoor=outdoor,
            hiking=hiking,
            biking=biking,
            fishing=fishing,
            camping=camping,
            climbing=climbing,
            kayaking=kayaking,
            swimming=swimming,
            picnic_area=picnic_area,
            wildlife_watching=wildlife_watching,
            photography=photography,
            bbq=bbq,
            campsite=campsite
        )

        # Add new spot to database
        db.session.add(new_spot)
        db.session.commit()

        return redirect(url_for('all_spots'))  # Redirect to the list of spots after adding

    # Display the add spot form for GET request
    return render_template('add_spot.html')




def validate_osm_coordinates(latitude, longitude):
    """
    Validate that the latitude and longitude have at least 5 decimal places.
    """
    # Convert latitude and longitude to strings and check if they have 5 decimal places
    lat_str = f"{latitude:.6f}"  # Format to 6 decimal places
    lon_str = f"{longitude:.6f}"  # Format to 6 decimal places

    # Check if latitude and longitude have at least 5 decimal places
    lat_decimal_places = len(lat_str.split('.')[1])
    lon_decimal_places = len(lon_str.split('.')[1])

    # OSM standard requires at least 5 decimal places for both latitude and longitude
    if lat_decimal_places >= 5 and lon_decimal_places >= 5:
        return True
    return False





# Edit a Spot (Admin Only)
@app.route('/spots/<int:spot_id>/edit', methods=['GET', 'POST'])
def edit_spot(spot_id):
    if 'user_id' not in session or not User.query.get(session['user_id']).is_admin:
        return render_template('403.html'), 403

    spot = Spot.query.get(spot_id)
    if not spot:
        return render_template('404.html', message="Spot not found"), 404

    if request.method == 'POST':
        spot.name = request.form['name']
        spot.description = request.form['description']
        spot.longitude = request.form['longitude']
        spot.latitude = request.form['latitude']
        spot.booking_required = 'booking_required' in request.form
        spot.car_park = 'car_park' in request.form
        spot.outdoor = 'outdoor' in request.form
        spot.hiking = 'hiking' in request.form
        spot.biking = 'biking' in request.form
        spot.fishing = 'fishing' in request.form
        spot.camping = 'camping' in request.form
        spot.climbing = 'climbing' in request.form
        spot.kayaking = 'kayaking' in request.form
        spot.swimming = 'swimming' in request.form
        spot.picnic_area = 'picnic_area' in request.form
        spot.wildlife_watching = 'wildlife_watching' in request.form
        spot.photography = 'photography' in request.form
        spot.bbq = 'bbq' in request.form
        spot.campsite = 'campsite' in request.form
        db.session.commit()
        return redirect(url_for('spot_by_id', spot_id=spot_id))

    return render_template('edit_spot.html', spot=spot)



# Bookings
@app.route('/bookings')
def user_bookings():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    bookings = Booking.query.filter_by(user_id=user_id).all()

    # Separate bookings into past, current, and future
    current_time = datetime.utcnow()
    past_bookings = [booking for booking in bookings if booking.end_time < current_time]
    future_bookings = [booking for booking in bookings if booking.start_time > current_time]
    current_bookings = [booking for booking in bookings if booking.start_time <= current_time <= booking.end_time]

    # Get weather forecast for future bookings
    future_booking_weather = {}
    for booking in future_bookings:
        weather_data = []
        current_day = booking.start_time
        while current_day <= booking.end_time:
            # Convert current_day to ISO format
            date_str = current_day.isoformat().split("T")[0]
            
            # Check if it will rain or snow on this day
            rain_or_snow = check_rain_or_snow_for_day(booking.spot.latitude, booking.spot.longitude, date_str)
            
            if rain_or_snow:
                weather_data.append({
                    "date": date_str,
                    "rain_or_snow": rain_or_snow
                })
            else:
                weather_data.append({
                    "date": date_str,
                    "rain_or_snow": None
                })

            # Move to the next day
            current_day += timedelta(days=1)

        future_booking_weather[booking.id] = weather_data

    return render_template('bookings.html', 
                           past_bookings=past_bookings, 
                           future_bookings=future_bookings, 
                           current_bookings=current_bookings,
                           future_booking_weather=future_booking_weather)



def get_rain_snow_times(day_data):
    """
    Given hourly weather data for a day, finds the start and end time for rain or snow.
    """
    rain_start, rain_end = None, None
    snow_start, snow_end = None, None

    for hour in day_data.get('hours', []):
        if hour.get('rain', 0) > 0:
            if not rain_start:
                rain_start = hour['datetime']
            rain_end = hour['datetime']
        if hour.get('snow', 0) > 0:
            if not snow_start:
                snow_start = hour['datetime']
            snow_end = hour['datetime']

    return {
        "rain": {"start": rain_start, "end": rain_end} if rain_start else None,
        "snow": {"start": snow_start, "end": snow_end} if snow_start else None
    }




@app.route('/', methods=['GET'])
def home():
    """
    Serve the homepage of the application.
    """
    return render_template('home.html')

@app.route('/about', methods=['GET'])
def about():
    """
    Serve the homepage of the application.
    """
    return render_template('about.html')




# Initialize the database
@app.before_first_request
def create_tables():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, port=5002)
    db.create_all()

