
import os

def check_players():
    print(f"CWD: {os.getcwd()}")
    base_path = "assets/graphics/images/player"
    print(f"Checking path: {os.path.abspath(base_path)}")
    
    if os.path.isdir(base_path):
        print("Directory exists.")
        found = []
        for d in os.listdir(base_path):
            full_p = os.path.join(base_path, d)
            if os.path.isdir(full_p) and not d.startswith("."):
                found.append(d)
        found.sort()
        print(f"Found players: {found}")
    else:
        print("Directory NOT found.")

if __name__ == "__main__":
    check_players()
