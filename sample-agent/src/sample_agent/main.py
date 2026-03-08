# SPDX-License-Identifier: Apache-2.0

import asyncio

from sample_agent import settings as settings_mod

settings = settings_mod.Settings()


async def main() -> None:
    print(f"Sample agent starting — targeting API at {settings.api_base_url}")

    # TODO: Implement HALO discovery and Agent Framework integration
    # 1. Use HttpPlugin to discover tools from the sample API
    # 2. Register discovered tools with Agent Framework
    # 3. Run an agent loop that invokes tools via HALO
    print("Agent not yet implemented — see halohttp.HttpPlugin for the client adapter.")


if __name__ == "__main__":
    asyncio.run(main())
