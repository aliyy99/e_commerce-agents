import asyncio
from backend.models.requests import CompareRequest, CompareSiteData
from backend.agents.compare_agent import run_compare_agent

async def main():
    req = CompareRequest(
        products=[
            CompareSiteData(
                site="Hepsiburada",
                url="https://www.hepsiburada.com/samsung-galaxy-s25-ultra-512-gb-12-gb-ram-samsung-turkiye-garantili-siyah-titanyum-p-HBCV00007MIDSU",
                product_name="Samsung Galaxy S25 Ultra 512 GB 12 GB Ram"
            ),
            CompareSiteData(
                site="Vatan",
                url="https://www.vatanbilgisayar.com/samsung-galaxy-s25-ultra-12-512-gb-akilli-telefon-titanyum-gumus.html",
                product_name="Samsung Galaxy S25 Ultra 512 GB 12 GB Ram"
            )
        ],
        locale="tr"
    )
    try:
        res = await run_compare_agent(req)
        print("SUCCESS")
        print(res)
    except Exception as e:
        import traceback
        traceback.print_exc()

asyncio.run(main())
