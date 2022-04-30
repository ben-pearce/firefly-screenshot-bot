# 📱➡️🐷 FireflyIII Screenshot Import Bot

A Telegram bot for importing screenshots of financial apps directly into 
[FireflyIII](https://github.com/firefly-iii/firefly-iii) open-source finance 
manager.

## The problem?
I find FireflyIII is a fantastic way to keep track of your finances, all of your asset accounts in one place and hosted in a place you know for sure is secure and private. The developer of FireflyIII also provides a very useful tool for importing data into your accounts call [fidi](https://docs.firefly-iii.org/data-importer) (Firefly-Data-Importer). fidi supports importing data from various sources such as csv and even open banking APIs like Nordigen.

The problem I find is specifically with accounts that provide **no** open-banking API, and **no** other way to easily export-import your data into Firefly. These are normally savings or investment type accounts such as [Trading212](https://www.trading212.com/) or [Moneybox](https://www.moneyboxapp.com/). Even for accounts where there may be some alternative API they have provided which isn't directly compatible with fidi, writing a script specifically for importing data from that account becomes cumbersome and wastes your precious time.

## The solution
Luckily, these types of accounts will usually at a bare-minimum have _some_ type of online banking portal or mobile app.

I decided the quickest way to import this data would be in the form of a screenshot directly from the banks site or app. 

This telegram bot enables you to share a screenshot of the banking app or site in question and will quickly recognise your new balance and update an asset account within Firefly accordingly using Firefly's open API.

![ffbot-diagram](https://user-images.githubusercontent.com/32749673/166115019-b5ef7efc-4b05-40f7-b7d5-5a148da97fe2.png)

## Installation

Recommended installation is with Docker.

### docker-compose

```yml
version: "3.4"
services:
  fsib:
    image: ghcr.io/ben-pearce/firefly-screenshot-bot
    container_name: fsib
    environment: 
      - TELEGRAM_TOKEN= # Telegram bot token
      - FIREFLY_BASE_URL=http://firefly
      - FIREFLY_TOKEN= # Firefly token
      - TELEGRAM_ALLOWED_USERS= # Telegram user IDs
    volumes:
      - /path/to/storage:/storage
    restart: unless-stopped
```

### docker cli

```yml
docker run -d \
  --name=fsib
  -e TELEGRAM_TOKEN= `# Telegram bot token` \
  -e FIREFLY_BASE_URL=http://firefly \
  -e FIREFLY_TOKEN= `# Firefly token` \
  -e TELEGRAM_ALLOWED_USERS= `# Telegram user IDs` \
  -v /path/to/storage:/storage \
  --restart unless-stopped \
  ghcr.io/ben-pearce/firefly-screenshot-bot
```

## Environment Variables

| Variable | Function
| :----: | --- 
| `TELEGRAM_TOKEN` | Telegram bot token.
| `FIREFLY_BASE_URL` | The base URL wher your FireflyIII API is accessible.
| `FIREFLY_TOKEN` | FireflyIII API Token.
| `TELEGRAM_ALLOWED_USERS` | Comma-separated list of Telegram user IDs to restrict access.
| `BOT_STORAGE_PATH` | Storage path of bot user data.
| `BOT_SCREENSHOT_HASH_ALGO` | Options are `colorhash`, `average_hash`, `phash`, `dhash`. (Recommended: `colorhash`)
| `BOT_SCREENSHOT_THRESHOLD` | Threshold value to compare image hashes.
| `BOT_BALANCE_DESC` | The transaction description used when creating new FireflyIII transactions.

## Commands

| Command | Function
| :----: | --- 
| `/start` | Register your telegram profile with the bot.
| `/setup` | Start the setup wizard to configure a Firefly asset account with the bot.
| `/manage` | Starts the management wizard where you can reset your profile or remove configured asset accounts.
| `/help` | Shows a help page.

To update a balance, simply send the bot a screenshot and it will do its best to work out which account the screenshot is for and update the balance accordingly. It doesn't even matter if the screenshot is slightly different from when you set the account up, so long as it is _some-what_ familiar, the bot will just work it out using computer vision.

In the event it isn't sure which account the screenshot is for, it will ask you. 

## FAQ

**Can multiple telegram users register with the bot?**

The bot should be ran by you for use with your own Firefly instance only, this both keeps your data safe (since it isn't stored anywhere you have no control of), and keeps the design of the bot simple.
Whilst it is possible to register multiple Telegram users, they can only control a single Firefly instance, there is no concept of user accounts currently.

**Can I import individual transactions?**

Eventually I'd like the bot to be able to scan a list of transactions from an image and import them as transactions within Firefly. Currently, the bot just scans a single value (a balance) and creates a new transaction within Firefly to keep your balance in sync.

**What are relationships?**

When you register an asset account and the bot sees the screenshot for the new account is similar to one for another account, it will ask if you want to create a relationship. If you set the account up as a relationship with another, it will assume both account balances can be seen from the same screenshot, and update both at once from a single screenshot when you next come to update the balance next time around.

**Can I manipulate the Firefly transaction the bot creates (i.e. Description, Type etc)?**

The bot creates a transaction with the destination account set and a desciption which is configurable but is by default set as "Bot Balance Update". You may then use [FireflyIII's automation rules](https://docs.firefly-iii.org/firefly-iii/pages-and-features/rules/) to manipulate transactions further. :)