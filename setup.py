import setuptools as setuptools

setuptools.setup(
    name='firefly_screenshot_bot',
    version='0.0.3',
    author='Ben Pearce',
    author_email='ben.pearce@sky.com',
    description='Telegram bot for importing screenshots into FireflyIII',
    license='MIT',
    url='https://github.com/ben-pearce/firefly-screenshot-bot',
    packages=['firefly_bot', 'firefly_bot.setup', 'firefly_bot.manage', 'firefly_bot.balance']
)
