import asyncio
from app.web_mvp.knowledge import retrieve_verified

async def main():
    res = await retrieve_verified('Who is the HOD of CSE Data Science?', 'FACULTY_INFORMATION', 'Computer Science and Engineering (Data Science)')
    print('RESULT:')
    for doc in res:
        print(doc.get('name') or doc.get('title'))

asyncio.run(main())
