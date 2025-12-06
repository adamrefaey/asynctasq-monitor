import asyncio

from asynctasq.config import set_global_config
from asynctasq.core.task import task

# 1. Configure (or use environment variables)
set_global_config(driver="redis", redis_url="redis://localhost:6379", redis_password=None)


# 2. Define a task
@task
async def send_email(to: str, subject: str, body: str):
    print(f"Sending email to {to}: {subject}")
    await asyncio.sleep(1)  # Simulate email sending
    return f"Email sent to {to}"


# 3. Dispatch the task
async def main():
    for i in range(10):
        task_id = await send_email.dispatch(
            to=f"user{i}@example.com", subject=f"Welcome {i}!", body="Welcome to our platform!"
        )
        print(f"Task dispatched: {task_id}")


if __name__ == "__main__":
    asyncio.run(main())
