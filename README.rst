.. image:: https://readthedocs.org/projects/zipline-trader/badge/?version=latest
   :target: https://zipline-trader.readthedocs.io/en/latest/?badge=latest
   :alt: Documentation Status
.. image:: https://github.com/gwhk/zipline-trader/workflows/Zipline%20CI%20(Ubuntu)/badge.svg
   :target: https://github.com/gwhk/zipline-trader/workflows/Zipline%20CI%20(Ubuntu)/badge.svg
   :alt: Github Actions
.. image:: https://github.com/gwhk/zipline-trader/workflows/Zipline%20CI%20(Windows)/badge.svg
   :target: https://github.com/gwhk/zipline-trader/workflows/Zipline%20CI%20(Windows)/badge.svg
   :alt: Github Actions
.. image:: https://github.com/gwhk/zipline-trader/workflows/Zipline%20CI%20(macOS)/badge.svg
   :target: https://github.com/gwhk/zipline-trader/workflows/Zipline%20CI%20(macOS)/badge.svg
   :alt: Github Actions

|

.. image:: ./images/zipline-live2.small.png
    :target: https://github.com/gwhk/zipline-trader
    :width: 212px
    :align: center
    :alt: zipline-live

zipline-trader
==============

Welcome to zipline-trader, the on-premise trading platform built on top of Quantopian's
`zipline <https://github.com/quantopian/zipline>`_.

This project is meant to be used for backtesting/paper/live trading with one the following brokers:
 * Interactive Brokers
 * Alpaca


Please `Read The Docs <https://zipline-trader.readthedocs.io/en/latest/index.html#>`_

Latest compilable Python version is 3.9, instructions to install:
 * wget https://www.python.org/ftp/python/3.9.18/Python-3.9.18.tgz
 * tar -xzf Python-3.9.18.tgz
 * cd Python-3.9.18
 * ./configure --enable-optimizations  -with-lto  --with-pydebug
 * make -j 4
 * sudo make altinstall

