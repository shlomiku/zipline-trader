
Zipline Trader
=================

Welcome to `zipline-trader`_, the on-premise trading platform built on top of Quantopian's
`zipline <https://github.com/quantopian/zipline>`_.

Quantopian closed their services, so this project tries to be a suitable replacement.

zipline-trader is based on previous projects and work:

- `zipline <https://github.com/quantopian/zipline>`_ project.
- `zipline-live <http://www.zipline-live.io>`_ project.
- `zipline-live2 <https://github.com/gwhk/zipline-live2>`_ project.

zipline-live and zipline-live2 are past iterations of this project and this is the up to date project.

New in v1.6.0
===================
* Running on python 3.6 or 3.7
* Using pandas<=1.1.5 and numpy<=1.19.x
* Using postgres as a ingested DB backend
* alpha-vantage bundle
* video tutorials for working with this package: `playlist`_

.. raw:: html

    <iframe width="660" height="315" src="https://www.youtube.com/embed/gsUnCjl5mrg" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>

Special thanks to `@atarax`_ for contributing to this release of zipline-trader

abstract
-----------

After Quantopian closed their services, this project was updated to supply a suitable and
sustainable replacement for users that want to run their algorithmic trading on their own without
relying on online services that may disappear one day. It  is designed to be an extensible, drop-in replacement for
zipline with multiple brokerage support to enable on premise trading of zipline algorithms.

I recommend using python 3.6, but some work has been done to achieve the same results on 3.7. More work is needed though.

Supported Data Sources
--------------------------
Out of the box, zipline-trader supports Alpaca and alpha vantage as a free data sources . You could use the quantopian-quandl bundle used
in old zipline versions or any other bundle you create (how to create a bundle on a later section)

Supported Brokers
------------------------
Currently 2 brokers are supported:
 * Alpaca
 * IB


.. _`zipline-trader` : https://github.com/gwhk/zipline-trader
.. _`playlist` : https://youtu.be/gsUnCjl5mrg
.. _`@atarax` : https://github.com/atarax/
