import pika
import pymongo
import configparser
import logging

config = configparser.ConfigParser()
config.read('config.ini')

AMPQ_URL = config['RabbitMQ']['AMQP_URL']


def get_single_story():
    try:
        # Parse the AMQP URL with credentials
        parameters = pika.URLParameters(AMPQ_URL)

        # Establish a connection
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()


        # Get a single message from the queue
        method, properties, body = channel.basic_get(queue='stories', auto_ack=True)

        # Return the message body (i.e. the story)
        return body.decode('utf-8') if body else None
    except Exception as e:
        logging.error(e)
        return None

def write_story_to_mongodb(story):
    # Connect to MongoDB using a context manager
    with pymongo.MongoClient('mongodb://localhost:27017/') as client:
        # Select the database and collection
        db = client['stories']
        collection = db['children_stories']

        # Insert the story into the collection
        result = collection.insert_one({'story': story})

        # Return the ID of the inserted document
        return result.inserted_id

