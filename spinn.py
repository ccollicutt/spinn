#!/usr/bin/env python

import sys
import yaml
import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

BOTO_ERROR = False
IPYTHON_ERROR = False

try:
    from boto import ec2
except:
    BOTO_ERROR = True

try:
    from IPython import embed
except:
    IPYTHON_ERROR = True

def get_spot_price(client, history_length_days, instance_type):
    now = datetime.datetime.now()
    before = now - datetime.timedelta(days=history_length_days)
    instance_type = instance_type 
    price_history = client.get_spot_price_history(
        start_time = before.isoformat(),
        end_time = now.isoformat(),
        instance_type = instance_type, 
        product_description = 'Linux/UNIX')

    return price_history

if __name__ == "__main__":

  if BOTO_ERROR:
     print "ERROR: Failed to import boto library, exiting..."
     print "INFO: pip install boto"
     sys.exit(1)

  #
  # Read config
  # 

  config_file = open("./spinn.conf", "r")
  config_yaml = yaml.load(config_file)

  if not config_yaml.has_key('region'):
    default_region = 'us-west-1'
  else:
    default_region = config_yaml.get('region')

  if not config_yaml.has_key('history_length_days'):
    history_length_days = config_yaml.get('history_length_days')
  else:
    history_length_days = 7 

  if not config_yaml.has_key('plot_image_name'):
    plot_image_name = 'plot.png'
  else:
    plot_image_name = config_yaml.get('plot_image_name')

  if not config_yaml.has_key('instance_type'):
    instance_type = 'c3.xlarge'
  else:
    instance_type = config_yaml.get('instance_type')

  if not config_yaml.has_key('outliers_multiplier'):
    outliers_multiplier = 20
  else:
    outliers_multiplier = config_yaml.get('outliers_multiplier')

  #
  # Make connection to region
  # - Boto will use AWS credentials...
  #

  try:
    client = ec2.connect_to_region(default_region)
    print "INFO: Connected to ec2"
  except:
    print "ERROR: Client connection to ec2 failed, exiting..."
    sys.exit(1)

  print("INFO: Getting spot instance prices")
  try:
    prices = get_spot_price(
      client, 
      history_length_days,
      instance_type
    )
  except:
    print("ERROR: Failed to get prices, exiting...")
    sys.exit(1)

  if len(prices) == 0:
    print("ERROR: Error getting prices, likely variables, exiting...")
    sys.exit(1)
  
  print("INFO: Number of prices (currently max 1000): " + str(len(prices)))

  azs = {}
  all_prices = []
  # ugly...just trying to get rid of some outliers...
  for h in prices:
    if h.availability_zone not in azs:
      print("INFO: adding az " + h.availability_zone)
      azs[h.availability_zone] = {}
      azs[h.availability_zone]['prices'] = []
      azs[h.availability_zone]['timestamps'] = []

    #if h.price < max_value:
    # magic!
    ts = mdates.datestr2num(h.timestamp)
    azs[h.availability_zone]['timestamps'].append(ts)
    azs[h.availability_zone]['prices'].append(h.price)
    # load up all prices to get an avg later...
    all_prices.append(h.price)

  #
  # Finally plot...
  #

  fig = plt.figure()
  fig.set_size_inches(18.5, 10.5)
  graph = fig.add_subplot(111)
  graph.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))

  # plot all the availabilty_zones that were returned
  for az in azs:
    timestamps = azs[az]['timestamps']
    prices = azs[az]['prices']
    graph.plot_date(timestamps, prices, 'o-', label=az )

  fig.autofmt_xdate()
  plt.locator_params(nbins=5)
  plt.legend(loc=2) # top left
  plt.ylabel("Money")
  plt.xlabel("Time")
  plt.savefig(plot_image_name)
  print("INFO: Writing image to " + plot_image_name)
  # ugly...
  avg = sum(all_prices) / len(all_prices)
  print("INFO: Average price for all availability zones: " + str(avg))
  print("INFO: Done!")
