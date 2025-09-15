import os

def run_command(user_input):
    # ⚠ Vulnérabilité : injection de commande système
    os.system("echo " + user_input)

if __name__ == "__main__":
    run_command("; rm -rf /")  # test d'injection

# temp.py
SECRET_KEY = "1234567890abcdef"  # secret en clair
