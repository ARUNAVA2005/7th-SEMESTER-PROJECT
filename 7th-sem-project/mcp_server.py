"""Optional MCP server exposing job search tools to compatible AI clients."""

from mcp.server.fastmcp import FastMCP

from services.jobs import fetch_jobs, rank_jobs

mcp = FastMCP("Career Compass Job Tools")


@mcp.tool()
def fetch_linkedin(query: str, location: str = "India", limit: int = 30) -> list[dict]:
    """Fetch and relevance-rank LinkedIn jobs via the configured Apify Actor."""
    jobs, _ = fetch_jobs(query, location, min(max(limit, 1), 60))
    return rank_jobs([job for job in jobs if job["source"] in {"LinkedIn", "Demo listing"}], query, query)[:limit]


@mcp.tool()
def fetch_naukri(query: str, location: str = "India", limit: int = 30) -> list[dict]:
    """Fetch and relevance-rank Naukri jobs via the configured Apify Actor."""
    jobs, _ = fetch_jobs(query, location, min(max(limit, 1), 60))
    return rank_jobs([job for job in jobs if job["source"] in {"Naukri", "Demo listing"}], query, query)[:limit]


if __name__ == "__main__":
    mcp.run()
