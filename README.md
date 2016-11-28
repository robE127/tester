# tester

This Python 3 script allows the user to run user defined commands and scripts while monitoring essential performance metrics.

You can use it in the following manner to run your test plan:

./tester.py config.ini -r

There is also a setup function:

./tester.py config.ini -s

As well as a cleanup function:

./tester.py config.ini -c

You can also use all the options together to setup, run the test plan, and cleanup:

./tester.py config.ini -s -r -c

See my sample config.ini file to see what you can do with it.
