"""asyncio + httpx load generator for CloudScale.

Hits /api/stress through CloudFront (each request burns CPU on an app instance for --ms) and prints
request rate, error count and latency percentiles every few seconds, then a summary.

Prerequisite (needs approval, it is a change in AWS): turn the stress endpoint on first:
  aws ssm put-parameter --name /cloudscale/enable-stress --value true --overwrite --type String
and turn it off afterwards (value false).

Usage:
  python scripts/load_test.py --url https://<cloudfront-domain> --concurrency 40 --duration 900 --ms 300
"""
import argparse
import asyncio
import statistics
import time

import httpx


def pct(values, p):
    if not values:
        return 0.0
    values = sorted(values)
    return values[min(len(values) - 1, int(len(values) * p / 100))]


async def worker(client, url, stop_at, results):
    while time.monotonic() < stop_at:
        start = time.monotonic()
        try:
            r = await client.get(url)
            ok = r.status_code == 200
            code = r.status_code
        except httpx.HTTPError:
            ok, code = False, 0
        results.append((time.monotonic(), time.monotonic() - start, ok, code))


async def reporter(results, stop_at, every):
    seen = 0
    t0 = time.monotonic()
    while time.monotonic() < stop_at:
        await asyncio.sleep(every)
        window = results[seen:]
        seen = len(results)
        if not window:
            continue
        lat = [w[1] for w in window]
        errs = sum(1 for w in window if not w[2])
        print(f"t+{time.monotonic() - t0:5.0f}s  {len(window) / every:6.1f} req/s  errors={errs:<4d} "
              f"p50={pct(lat, 50) * 1000:6.0f}ms  p90={pct(lat, 90) * 1000:6.0f}ms  "
              f"p99={pct(lat, 99) * 1000:6.0f}ms", flush=True)


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True, help="e.g. https://dxxxx.cloudfront.net")
    ap.add_argument("--concurrency", type=int, default=40)
    ap.add_argument("--duration", type=int, default=600, help="seconds")
    ap.add_argument("--ms", type=int, default=300, help="CPU burn per request")
    ap.add_argument("--report-every", type=int, default=10)
    args = ap.parse_args()

    target = f"{args.url.rstrip('/')}/api/stress?ms={args.ms}"
    results = []
    stop_at = time.monotonic() + args.duration
    limits = httpx.Limits(max_connections=args.concurrency, max_keepalive_connections=args.concurrency)
    async with httpx.AsyncClient(timeout=30, limits=limits, http2=False) as client:
        probe = await client.get(target)
        if probe.status_code != 200:
            raise SystemExit(f"{target} returned {probe.status_code}; is /cloudscale/enable-stress set to true?")
        print(f"target {target}  concurrency={args.concurrency}  duration={args.duration}s", flush=True)
        tasks = [asyncio.create_task(worker(client, target, stop_at, results)) for _ in range(args.concurrency)]
        tasks.append(asyncio.create_task(reporter(results, stop_at, args.report_every)))
        await asyncio.gather(*tasks)

    lat = [r[1] for r in results]
    errs = sum(1 for r in results if not r[2])
    print("\n=== summary ===")
    print(f"requests: {len(results)}  errors: {errs}  avg rate: {len(results) / args.duration:.1f} req/s")
    if lat:
        print(f"latency ms: mean={statistics.mean(lat) * 1000:.0f} p50={pct(lat, 50) * 1000:.0f} "
              f"p90={pct(lat, 90) * 1000:.0f} p99={pct(lat, 99) * 1000:.0f} max={max(lat) * 1000:.0f}")


if __name__ == "__main__":
    asyncio.run(main())
