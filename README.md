Sports Coordination System
Project Description
The Sports Coordination System is a web-based application developed to improve the management of sports activities within an institution.
The system provides a centralized platform where players, trainers, tournament organizers, and administrators can manage sports-related activities instead of relying mainly on WhatsApp messages, phone calls, and physical communication.

Main Features
* User registration and login
* Role-based access for players, trainers, tournament organizers, and administrators
* Player registration and team selection
* Trainer team management
* Player team-join requests
* Acceptance or rejection of player requests
* Training session scheduling
* Tournament scheduling and registration
* Player feedback management
* Separate dashboards for different users

Technologies Used
* Python
* Django
* MySQL
* HTML
* CSS
* Git and GitHub

User Roles

Player
Players can register, select a team, view their dashboard, access training information, and submit feedback.
Trainer
Trainers can create and manage teams, review player join requests, schedule training sessions, and manage their players.
Tournament Organizer
Tournament organizers can create tournament schedules and manage tournament-related activities.
Administrator
The administrator manages users and oversees the overall system.

How to Run the Project
1. Clone the repository:
git clone YOUR_REPOSITORY_LINK
2. Open the project folder:
cd YOUR_PROJECT_FOLDER
3. Create a virtual environment:
python -m venv venv
4. Activate the virtual environment.
Windows:
venv\Scripts\activate
5. Install the required packages:
pip install -r requirements.txt
1. Configure the MySQL database in settings.py.
2. Run the database migrations:
python manage.py migrate
8. Start the development server:
python manage.py runserver
9. Open the following address in a browser:
http://127.0.0.1:8000/

Project Contributors
* Benie Carla – Player and Trainer modules 
* Vicky Kanyama– Tournament Organizer and Administration modules
Academic Purpose
This system was developed as a collaborative university IT project. The repository demonstrates the implementation of the system and the modules developed by the contributors.
