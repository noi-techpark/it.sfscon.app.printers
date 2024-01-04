import asyncio

from telegram import Bot
from telegram.error import TelegramError

# Initialize the bot with your bot's token
bot = Bot(token='6857843143:AAFqZhPFwoJ4SS55-OBhqKXNhI_sC7DfRoo')

# Replace 'YOUR_CHAT_ID' with the actual chat ID or username
chat_id = '1036660676'

# Replace 'path_to_your_image.png' with the path to your image
image_path = '/tmp/label.png'


async def main():
    try:
        # Send the image
        with open(image_path, 'rb') as photo:
            await bot.send_photo(chat_id=chat_id, photo=photo)
    except TelegramError as e:
        print(f"An error occurred: {e.message}")


if __name__ == '__main__':
    asyncio.run(main())
