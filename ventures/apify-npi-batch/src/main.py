from .runtime import run
from .source import collect

async def main():
    await run(collect, 'provider-record')
