# Detailed Deployment Guide (Render + cron-job.org)

This guide provides baby steps on how to set up everything from scratch and deploy your Product Stock Finder bot to the cloud for free using Render. Because the bot stores its configuration in the Telegram chat itself, you don't need to worry about setting up a database.

---

## Part 1: Getting Your Telegram Credentials

You need 4 pieces of information from Telegram to make the bot work. Here is how to get each one:

### 1. `TELEGRAM_BOT_TOKEN`
This is the token that controls the bot itself.
1. Open the Telegram app and search for **@BotFather**.
2. Send the message `/newbot` to create a new bot.
3. Choose a display name (e.g., "Product Stock Finder").
4. Choose a username (must end in `bot`, e.g., `MyStockFinderBot`).
5. BotFather will reply with a long token (e.g., `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`). 
6. **Save this token** as your `TELEGRAM_BOT_TOKEN`.

### 2. `TELEGRAM_API_ID` & `TELEGRAM_API_HASH`
These are your developer credentials required by the Telethon library.
1. Go to [my.telegram.org](https://my.telegram.org) and log in with your phone number.
2. Click on **API development tools**.
3. Create a new application (you can name it anything, e.g., "Stock Bot").
4. Once created, you will see your **App api_id** (a number) and **App api_hash** (a long text string).
5. **Save these** as your `TELEGRAM_API_ID` and `TELEGRAM_API_HASH`.

### 3. `TELEGRAM_USER_ID`
This tells the bot who its owner is, so it only listens to YOU.
1. Open Telegram and search for **@userinfobot** or **@RawDataBot**.
2. Send `/start`.
3. The bot will reply with your profile info. Look for the `"Id": 12345678` field.
4. **Save this number** as your `TELEGRAM_USER_ID`.

*(Now that you have these 4 values, you are ready to deploy!)*

---

## Part 2: Deploying to Render (Free)

Render will run your bot's code in the cloud.

1. **Upload Code to GitHub:**
   - Create a free GitHub account if you don't have one.
   - Create a new Private or Public repository.
   - Upload all the files from your `Product Stock Finder` folder (especially `bot.py` and `requirements.txt`) to that repository.

2. **Create the Render Web Service:**
   - Go to [Render.com](https://render.com) and sign up/log in.
   - Click the **New +** button at the top and select **Web Service**.
   - Connect your GitHub account and select the repository you just created.
   - On the configuration page, fill out the following:
     - **Name**: (Anything, e.g., `my-stock-bot`)
     - **Environment**: `Python 3`
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `python bot.py`
     - **Instance Type**: `Free`

3. **Add the Environment Variables:**
   - Scroll down to the **Environment Variables** section on Render.
   - Click **Add Environment Variable** 4 times and enter the values you got in Part 1:
     - Key: `TELEGRAM_API_ID` | Value: *(Your API ID)*
     - Key: `TELEGRAM_API_HASH` | Value: *(Your API Hash)*
     - Key: `TELEGRAM_BOT_TOKEN` | Value: *(Your Bot Token)*
     - Key: `TELEGRAM_USER_ID` | Value: *(Your User ID)*
   - *(Note: Render will automatically add a `PORT` variable in the background, which the bot needs for the next step).*

4. **Deploy:**
   - Click **Create Web Service**. 
   - Wait a few minutes. You will see the logs saying "Bot is online and ready!".
   - **Important:** At the top left of your Render dashboard, copy the URL Render gave you (e.g., `https://my-stock-bot.onrender.com`).

---

## Part 3: Keeping the Bot Awake (cron-job.org)

Render's free tier goes to "sleep" if it doesn't receive web traffic for 15 minutes. To keep your bot checking stock 24/7, we use a free service to ping that URL every 10 minutes.

1. Go to [cron-job.org](https://cron-job.org/) and create a free account.
2. Once logged in, click **CREATE CRONJOB** in the top right.
3. Fill out the details:
   - **Title**: `Keep Stock Bot Awake`
   - **URL**: Paste the Render URL you copied in Part 2 (e.g., `https://my-stock-bot.onrender.com`).
   - **Execution schedule**: Choose **User-defined**.
   - Set the interval to run every **10 minutes**.
4. Click **Create** at the bottom.

**You're all done!** 
The cron-job will now visit your bot's Render URL every 10 minutes. The built-in web server in `bot.py` will respond, keeping the server awake indefinitely so your stock checker background loop never stops. Go to Telegram and message your bot `/start`!
