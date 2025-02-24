# EZ Journal

EZ Journal is a lightweight production journal web application built with Flask. It enables authorized users to create, edit, and delete journal entries with rich text content using the Quill editor. The app uses a PIN-based authentication system with a lockout mechanism after three failed attempts, and it supports viewer-based permissions so that all users can see who has access to each entry.

## Features

- **PIN-Based Authentication & Lockout**  
  - Users log in using a PIN.  
  - After three failed login attempts, the user is locked out for one hour.  
  - The login page shows the number of remaining attempts and, after the first failure, suggests using a birthdate in MMDDYYYY format.

- **Journal Entry Management**  
  - Editors can add, edit, and delete journal entries.  
  - Each entry includes a title, rich text content (powered by Quill), date/time stamps, and viewer permissions.

- **Viewer Permissions**  
  - Each entry can have a list of viewers.  
  - The viewers list is displayed at the bottom of each entry for all users.

- **Responsive Design**  
  - The front end uses custom CSS for a clean, responsive layout, including a mobile-friendly sidebar.

## Technologies Used

- **Backend:** Python, Flask, Flask-SQLAlchemy, Flask-Login  
- **Frontend:** HTML, CSS, JavaScript, Quill Rich Text Editor  
- **Database:** SQLite

## Installation

1. **Clone the Repository:**

    git clone https://github.com/blahpunk/ez_journal.git  
    cd ez_journal

2. **Set Up a Virtual Environment (Recommended):**

    python3 -m venv venv  
    source venv/bin/activate  
    (On Windows: venv\Scripts\activate)

3. **Install Dependencies:**

    pip install -r requirements.txt

4. **Configuration:**  
   You can modify the settings in `app.py` (such as `SECRET_KEY` or `SQLALCHEMY_DATABASE_URI`) as needed.

5. **Run the Application:**

    python app.py

   The application will be available at:  
   http://0.0.0.0:4242/journal

## Usage

- **Login:**  
  Access the login page at `/journal/login`. Use the default admin PIN `0000` (you can change this later).

- **Journal Entries:**  
  Once logged in as an editor, you can create, update, or delete entries. All users will see the list of viewers for each entry at the bottom.

- **Manage PINs:**  
  The "Manage PINs" page allows editors to add, update, or delete viewer PINs.

## Contributing

Contributions, issues, and feature requests are welcome!  
Feel free to check the [issues page](https://github.com/blahpunk/ez_journal/issues).

## License

This project is licensed under the MIT License.
