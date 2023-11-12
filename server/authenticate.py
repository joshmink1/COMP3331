from exceptions import InvalidUsername, InvalidPassword

def authenticate():
    print("=====Authentication=====")
    username = input("Enter your username: ")
    correct_pass = read_cred_file(username)
    print(correct_pass)
    password = input("Enter your password: ")
    if password != correct_pass:
        raise InvalidPassword
    return

def verify_user(username):
    with open('credentials.txt', 'r') as f:
        for line in f:
            user = line.split(' ')
            if (user[0] == username):
                return
    raise InvalidUsername 

def verify_pass(username, password):
    with open('credentials.txt', 'r') as f:
        for line in f:
            user = line.split(' ')
            if (user[0] == username and user[1].strip() == password.strip()):
                return
    raise InvalidPassword

