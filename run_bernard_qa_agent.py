
import sys
import os
import asyncio
from pathlib import Path
from browser_use import Agent, Browser, BrowserProfile, ChatOpenAI


async def main():
    # Get login info and directions from environment variables (set in workflow or locally)
    login_user = '6thph8yu2o@vvatxiy.com'
    login_pass ='Testing123!'
    directions = 'go to app.bernieportal.com Log in first, then perform the following steps:'

    # Concatenate info to the task
    full_task = f"{directions}\nLogin with user: {login_user} and password: {login_pass}\n{task}"

    # Set up headless browser profile
    profile = BrowserProfile(headless=True)
    browser_session = Browser(browser_profile=profile, record_video_dir=Path('./tmp/recordings'))
    agent = Agent(
        task=full_task,
        llm=ChatOpenAI(model='gpt-5-mini'),
        browser_session=browser_session,
    )
    await agent.run(max_steps=100)
    print('Check ./tmp/recordings for the video!')

if __name__ == '__main__':
    asyncio.run(main())
