import logging
import os
import pathlib

import firefly_iii_client
import i18n
import yaml

with open('./config.yml', 'r') as f:
    config = yaml.load(f, Loader=yaml.FullLoader)

i18n.load_path.append(os.path.join(pathlib.Path(__file__).parent.resolve(), '../locale'))

logging.basicConfig(**config.get('bot').get('logging'))

ff_configuration = firefly_iii_client.Configuration(
    **config.get('firefly')
)
