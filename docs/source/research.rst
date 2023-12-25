Research & backtesting in the Notebook environment
===================================================
| To run your research environment you first need to make sure jupyter is installed.
| Follow the instructions in Jupyter.org_

.. code-block::

    e.g. pip install notebook

| Start your Jupyter server

.. code-block::

    jupyter notebook

| You might need to add the jupyter kernel to be able to work with your virtual environment.
| This should get it working, and search online if you face issue:

.. code-block:: sh

    pip install ipykernel
    python -m ipykernel install --user --name zipline-trader

.. raw:: html

    <iframe width="660" height="315" src="https://www.youtube.com/embed/mPgQvEVAoOA" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>

Working With The Research Environment
-----------------------------------------
| This was one of Quantopian's strengths and now you could run it locally too.
| In the next few examples we will see how to:

* Load your Alpaca (or any other) data bundle
* How to get pricing data from the bundle
* How to create and run a pipeline
* How tu run a backtest INSIDE the notebook (using python files will follow)
* How to analyze your results with pyfolio (for that you will need to install `pyfolio`_)


Loading Your Data Bundle
-----------------------------
| Now that you have a jupyter notebook running you could load your previously ingested data bundle.
| Follow this notebook for a usage example: `Load Data Bundle`_.

.. _Load Data Bundle: notebooks/LoadDataBundle.ipynb

.. _`Jupyter.org` : https://jupyter.org/install

.. raw:: html

    <iframe width="660" height="315" src="https://www.youtube.com/embed/AYLUDCBmqB4" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>

Simple Pipeline
--------------------------
| You can work with pipeline just as it was on Quantopian, and in the following example
  you could see hwo to create a simple pipeline and get the data:  `Simple Pipeline`_.

.. _Simple Pipeline: notebooks/SimplePipeline.ipynb

.. raw:: html

    <iframe width="660" height="315" src="https://www.youtube.com/embed/BIIHtP0m5xk" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>


Factors and Alphalens
--------------------------------
| Factors could be used to filter and/or rank your pipeline output and help you choose the better
| stocks to trade for your scenario. Quantopian created `Alphalens`_ to help you analyze the quality
| of your factors.
| This package is not maintained by quantopian anymore, so I recommend installing from my fork (I had to fix some stuff
  to make it work properly). Do this:

 .. code-block:: sh

    pip install git+https://github.com/gwhk/alphalens#egg=alphalens

Sector Classifier
)))))))))))))))))))))
| I added a builtin Sector classifier called ``ZiplineTraderSector``. It is based on the work in https://github.com/pbharrin/alpha-compiler.
| It allows you to work in specific sectors inside your universe. e.g: analyze how tech stocks respond to a certain factor.
| In the following example we can see how to use it on some factors we create. `Alphalens Example`_.

.. _Alphalens Example: notebooks/Alphalens.ipynb

.. raw:: html

    <iframe width="660" height="315" src="https://www.youtube.com/embed/8P34shf0dqY" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>

Run and analyze a backtest
--------------------------
| Running a backtest is the way to test your ideas. You could do it inside a notebook
  or in your python IDE (your choice).
| The advantage of using the notebook is the ability
  to use Pyfolio to analyze the results in a simple manner as could be seen here: `Bactesting`_.

.. _Bactesting: notebooks/backtest.ipynb

.. raw:: html

    <iframe width="660" height="315" src="https://www.youtube.com/embed/BIIHtP0m5xk" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>

.. _`pyfolio` : https://github.com/quantopian/pyfolio
.. _`Alphalens` : https://github.com/quantopian/alphalens
