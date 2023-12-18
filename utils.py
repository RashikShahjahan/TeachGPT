import pika
import pymongo


def get_single_story():
    with pika.BlockingConnection(pika.ConnectionParameters('localhost')) as connection:
        channel = connection.channel()

        # Declare the queue where we want to read the story from
        channel.queue_declare(queue='children_stories')

        # Get a single message from the queue
        method, properties, body = channel.basic_get(queue='children_stories', auto_ack=True)

        # Return the message body (i.e. the story)
        return body.decode('utf-8') if body else None


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

