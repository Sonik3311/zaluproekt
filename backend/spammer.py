import requests
import json
from random import randint
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

x = 0
y = 0

max_x = 99
max_y = 99
max_color = 4

def send_pixel_request(request_num):
    """Function to send a single pixel request"""
    url = "http://localhost:8080/ColorPixel"
    headers = {"Content-Type": "application/json"}

    global x, y, max_x, max_y, max_color
    x += 1
    if x > max_x:
        y += 1
        x = 0

    payload = {
        "x": x,
        "y": y,
        "color": 0,
    }

    try:
        response = requests.post(url, data=json.dumps(payload), headers=headers)
        return f"Request {request_num}: Status {response.status_code}"
    except Exception as e:
        return f"Request {request_num}: Error {str(e)}"

# Send 500 requests using thread pool
def main():
    start_time = time.time()

    # Using ThreadPoolExecutor with 10-50 threads (adjust based on your needs)
    with ThreadPoolExecutor(max_workers=100) as executor:
        # Submit all tasks
        futures = [executor.submit(send_pixel_request, i) for i in range(10_000)]

        # Wait for all tasks to complete and get results
        for future in as_completed(futures):
            result = future.result()
            print(result)

    end_time = time.time()
    print(f"Total time: {end_time - start_time:.2f} seconds")

if __name__ == "__main__":
    main()
