from setuptools import setup, find_packages

setup(
    name="product-stock-finder-bot",
    version="1.0.0",
    description="A Telegram bot that tracks product URLs and notifies you when they come back in stock.",
    author="gsah",
    packages=find_packages(),
    install_requires=[
        "telethon",
        "python-dotenv",
        "aiohttp",
        "beautifulsoup4",
        "cloudscraper",
        "colorama"
    ],
    entry_points={
        "console_scripts": [
            "start-bot=bot:main",
        ],
    },
)
