import random
import string

def generate_random_string(length):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def generate_shared_values(num_values, filename='shared_values.txt'):
    with open(filename, 'w') as f:
        for _ in range(num_values):
            value = generate_random_string(10)
            f.write(f"{value}\n")

if __name__ == "__main__":
    generate_shared_values(10)  
    print("Shared values file has been generated.")