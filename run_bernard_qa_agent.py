import asyncio
from pathlib import Path
from browser_use import Agent, Browser, ChatOpenAI

async def main():
    browser_session = Browser(record_video_dir=Path('./tmp/recordings'))
    agent = Agent(
        task='go to app.bernieportal.com ',
        llm=ChatOpenAI(model='gpt-5-mini'),
        browser_session=browser_session,
    )
    await agent.run(max_steps=100)
    print('Check ./tmp/recordings for the video!')

if __name__ == '__main__':
    asyncio.run(main())
