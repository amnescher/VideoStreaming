import asyncio
import aiohttp
import time
from collections import defaultdict
import logging

# Setup logging to write into a file
logging.basicConfig(filename='responsetime.log', level=logging.INFO, format='%(asctime)s: %(message)s')

async def send_request(session, url, data, headers, response_counter):
    async with session.post(url, json=data, headers=headers) as response:
        await response.text()  # Wait for response
        response_counter[round(time.time())] += 1  # Increment the count for the current second

async def send_requests_concurrently(batch_size, interval, duration):
    url = 'http://127.0.0.1:8000/inference'
    headers = {'accept': 'application/json', 'Content-Type': 'application/json'}
    data = {
        "img_path": "apple.jpeg",
        "camera_id": "string"
    }

    async with aiohttp.ClientSession() as session:
        tasks = []
        start_time = time.time()
        response_counter = defaultdict(int)  # Dictionary to count responses per second

        while time.time() - start_time < duration:
            batch_tasks = [asyncio.create_task(send_request(session, url, data, headers, response_counter)) for _ in range(batch_size)]
            tasks.extend(batch_tasks)
            await asyncio.sleep(interval)  # Wait for the specified interval before sending the next batch

        await asyncio.gather(*tasks)
        return response_counter

async def run_async_main():
    batch_size = 150
    interval_seconds = 0.2  # Interval between batches
    duration_seconds = 20
    response_counter = await send_requests_concurrently(batch_size, interval_seconds, duration_seconds)

    # Log the count of responses per second
    for second, count in response_counter.items():
        logging.info(f"Second {second}: {count} responses")

    # Optionally, print the log information
    print("Logging complete. Check 'responsetime.log' for details.")

# Execute the function using asyncio.run
asyncio.run(run_async_main())
