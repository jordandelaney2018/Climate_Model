import argparse
import datetime
import json

import requests

from db import get_connection


def parse_args():
  parser = argparse.ArgumentParser(description="Ingest UK carbon intensity data")
  parser.add_argument("--days", type=int, default=1)
  return parser.parse_args()


def to_api_datetime(value):
  return value.strftime("%Y-%m-%dT%H:%MZ")


def from_api_datetime(value):
  return datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))


def fetch_intensity_data(days):
  end_dt = datetime.datetime.now(datetime.timezone.utc).replace(second=0, microsecond=0)
  start_dt = end_dt - datetime.timedelta(days=days)

  # API requires start < end, even when days=0.
  if start_dt >= end_dt:
    start_dt = end_dt - datetime.timedelta(minutes=30)

  headers = {"Accept": "application/json"}
  start_str = to_api_datetime(start_dt)
  end_str = to_api_datetime(end_dt)

  response = requests.get(
    f"https://api.carbonintensity.org.uk/intensity/{start_str}/{end_str}",
    headers=headers,
    timeout=30,
  )
  response.raise_for_status()
  return response.json().get("data", [])


def upsert_rows(rows):
  if not rows:
    return 0

  sql = """
    INSERT INTO raw_carbon_intensity (
      from_time,
      to_time,
      forecast_intensity,
      actual_intensity,
      intensity_index,
      raw_payload
    )
    VALUES (%s, %s, %s, %s, %s, %s::jsonb)
    ON CONFLICT (from_time, to_time)
    DO UPDATE SET
      forecast_intensity = EXCLUDED.forecast_intensity,
      actual_intensity = EXCLUDED.actual_intensity,
      intensity_index = EXCLUDED.intensity_index,
      raw_payload = EXCLUDED.raw_payload,
      ingested_at = now()
  """

  values = []
  for row in rows:
    intensity = row.get("intensity", {})
    values.append(
      (
        from_api_datetime(row["from"]),
        from_api_datetime(row["to"]),
        intensity.get("forecast"),
        intensity.get("actual"),
        intensity.get("index"),
        json.dumps(row),
      )
    )

  with get_connection() as conn:
    with conn.cursor() as cursor:
      cursor.executemany(sql, values)
    conn.commit()

  return len(values)


def main():
  args = parse_args()
  rows = fetch_intensity_data(args.days)
  inserted = upsert_rows(rows)
  print({"rows_upserted": inserted})


if __name__ == "__main__":
  main()