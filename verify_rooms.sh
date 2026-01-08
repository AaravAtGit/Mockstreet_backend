#!/bin/bash

BASE_URL="http://localhost:8000"
RND=$((1 + $RANDOM % 10000))
EMAIL="roomtester${RND}@example.com"
USERNAME="roomtester${RND}"
PASSWORD="password123"

echo "Testing Rooms API with User: $USERNAME"

# 1. Register & Login
echo "Registering..."
REG_RES=$(curl -s -X POST "$BASE_URL/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"$EMAIL\", \"username\": \"$USERNAME\", \"password\": \"$PASSWORD\"}")
echo "Register Result: $REG_RES"

sleep 1

echo "Logging in..."
LOGIN_RES=$(curl -s -X POST "$BASE_URL/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=$EMAIL&password=$PASSWORD")
echo "Login Result: $LOGIN_RES"

TOKEN=$(echo $LOGIN_RES | grep -oP '"access_token":"\K[^"]+')

if [ -z "$TOKEN" ]; then
  echo "Login failed."
  exit 1
fi

# 2. Create Room
echo "Creating Room..."
CREATE_RES=$(curl -s -X POST "$BASE_URL/rooms/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Room", "symbol": "AAPL", "duration_seconds": 600}')

echo "Create Response: $CREATE_RES"

if [[ "$CREATE_RES" == *"\"player1_username\":\"$USERNAME\""* ]]; then
  echo "PASSED: Create Room response contains correct player1_username."
else
  echo "FAILED: Create Room response missing or incorrect player1_username."
  exit 1
fi

if [[ "$CREATE_RES" == *"\"player1_id\""* ]]; then
  echo "FAILED: Create Room response still contains player1_id."
  exit 1
fi

# 3. List Rooms
echo "Listing Rooms..."
LIST_RES=$(curl -s -X GET "$BASE_URL/rooms/" \
  -H "Authorization: Bearer $TOKEN")

if [[ "$LIST_RES" == *"\"player1_username\":\"$USERNAME\""* ]]; then
  echo "PASSED: List Rooms response contains player1_username."
else
  echo "FAILED: List Rooms response missing player1_username for the new room."
  # Note: logic allows for other rooms to exist, but our room should be there.
  exit 1
fi

echo "Rooms Verification Successful!"
