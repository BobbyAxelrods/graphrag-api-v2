from dotenv import load_dotenv
import openai, os 

load_dotenv()
openai.api_key = os.getenv("GRAPHRAG_API_KEY")

print(openai.models.list())


'''
SyncPage[Model](data=[Model(id='text-embedding-3-large', created=1705953180, object='model', owned_by='system'), Model(id='gpt-4o-mini', created=1721172741, object='model', owned_by='system')], object='list')
'''