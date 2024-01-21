import asyncio
import aiohttp
import time

async def send_request(session, url, data, headers):
    start_time = time.time()
    async with session.post(url, json=data, headers=headers) as response:
        await response.text()  # Wait for response
    end_time = time.time()
    return end_time - start_time  # Return the response time

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
        while time.time() - start_time < duration:
            batch_tasks = [asyncio.create_task(send_request(session, url, data, headers)) for _ in range(batch_size)]
            tasks.extend(batch_tasks)
            await asyncio.sleep(interval)  # Wait for the specified interval before sending the next batch

        response_times = await asyncio.gather(*tasks)
        return response_times

# Function to run the async function from a running event loop
async def run_async_main():
    batch_size = 150
    interval_seconds = 0.1  # Interval between batches
    duration_seconds = 120
    response_times = await send_requests_concurrently(batch_size, interval_seconds, duration_seconds)

    # Calculate the average response time
    average_response_time = sum(response_times) / len(response_times)
    print(f"Average Response Time: {average_response_time:.4f} seconds")

# Execute the function using asyncio.run
asyncio.run(run_async_main())
