# traffic-lights

*Due to the large dataset size, please email me to request the full dataset. Happy to set up a torrent or Resilio Sync folder for it. [shane@smiskol.com](mailto:shane@smiskol.com?subject=Traffic%20Lights%20Dataset%20Request)*

To start training, first unzip data.zip into the root directory of `traffic-lights` so that the directory tree looks like: `/traffic-lights/data/GREEN/etc.png`.

When you run train.py, it will then start a process of cropping and randomly transforming images from the dataset into the `/traffic-lights/data/.processed` directory.

Depending on the amount of data and your CPU, you may want to decrease the amount of data generator threads [as defined here](train_tf1.py#L202) as it's pretty heavy on system resources. An ETA will print approximately every 15 seconds to give you feedback on how long it will take.