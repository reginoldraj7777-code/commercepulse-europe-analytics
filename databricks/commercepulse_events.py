# Databricks notebook source
# Integration entry point; execution requires a user-managed Databricks workspace.
import re
from pyspark.sql import functions as F

dbutils.widgets.text('sourcePath', '')
dbutils.widgets.text('destinationSchema', '')
source = dbutils.widgets.get('sourcePath').rstrip('/')
schema = dbutils.widgets.get('destinationSchema')
if not source.startswith('/Volumes/') or not re.fullmatch(r'[A-Za-z_]\w*\.[A-Za-z_]\w*', schema):
    raise ValueError('Supply an existing Unity Catalog volume path and catalog.schema')
events = spark.read.parquet(source + '/events')
journeys = spark.read.parquet(source + '/journeys.parquet')
assert events.select('event_id').distinct().count() == events.count()
assert events.join(journeys.select('journey_id'), 'journey_id', 'left_anti').count() == 0
assert events.select('market').distinct().count() == 6
assert events.filter(F.col('engagement').isNull() | (F.col('engagement') < 0) | (F.col('engagement') >= 1)).count() == 0
market_channels = events.groupBy('market', 'channel').agg(F.count('*').alias('events'), F.countDistinct('journey_id').alias('journeys'))
# Fail if a table already exists: reruns cannot silently overwrite user data.
events.write.format('delta').mode('errorifexists').saveAsTable(schema + '.portfolio_events')
journeys.write.format('delta').mode('errorifexists').saveAsTable(schema + '.portfolio_journeys')
market_channels.write.format('delta').mode('errorifexists').saveAsTable(schema + '.portfolio_market_channels')
display(market_channels)
