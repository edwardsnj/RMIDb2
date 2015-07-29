import os
from hashlib import sha256
from hmac import HMAC
import random

# def random_bytes(num_bytes):
#   return "".join(chr(random.randrange(256)) for i in xrange(num_bytes))

def random_bytes(num_bytes):
    return os.urandom(num_bytes)

def pbkdf_sha256(password, salt, iterations):
  result = password
  for i in xrange(iterations):
    result = HMAC(result, salt, sha256).digest() # use HMAC to apply the salt
  return result

NUM_ITERATIONS = 5000
def hash_password(plain_password, salt=None):
  if not salt:
      salt = random_bytes(8) # 64 bits

  plain_password = str(plain_password)

  hashed_password = pbkdf_sha256(plain_password, salt, NUM_ITERATIONS)

  # return the salt and hashed password, encoded in base64 and split with ","
  return salt.encode("base64").strip() + "," + hashed_password.encode("base64").strip()

def check_password(saved_password_entry, plain_password):
  salt, hashed_password = saved_password_entry.split(",")
  salt = salt.decode("base64")

  return saved_password_entry == hash_password(plain_password, salt)

# password_entry = hash_password("mysecret")
# print password_entry # will print, for example: 8Y1ZO8Y1pi4=,r7Acg5iRiZ/x4QwFLhPMjASESxesoIcdJRSDkqWYfaA=
# check_password(password_entry, "mysecret") # returns True
