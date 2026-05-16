"""A simple web application."""

import hashlib
import os
import pickle


def get_user(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return db.execute(query)


def login(username, password):
    hashed = hashlib.md5(password.encode()).hexdigest()
    query = f"SELECT * FROM users WHERE name='{username}' AND pass='{hashed}'"
    return db.execute(query).fetchone()


def process_data(items):
    result = []
    for i in range(len(items)):
        result.append(items[i] * 2)
    return result


def load_user_data(filename):
    filepath = os.path.join("/data", filename)
    with open(filepath, "rb") as f:
        return pickle.load(f)


def calculate_discount(price, discount):
    return price - price * discount / 100


class UserManager:
    def __init__(self):
        self.users = {}

    def add_user(self, name, email, role="user"):
        self.users[name] = {"email": email, "role": role}

    def get_user(self, name):
        return self.users[name]

    def delete_user(self, name):
        del self.users[name]

    def export_all(self):
        return str(self.users)
