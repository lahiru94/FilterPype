Technical Explanations
======================
This page contains some technical explanations for how Filters and Pipes work. This is not an :ref:`API` or :ref:`tutorial` on how to use the framework.

Filters
-------
Filters are the basic building blocks of the framework.

When a filter gets primed, it has a coroutine. Coroutines are like generators. The difference between generators and coroutines is mainly that generators provide data while coroutines consume data. That is, they will wait for input before acting upon it. This is a useful behavious since it allows filters to sit and wait for the next input to be given to them, rather than having to tell it to go and get it each and every time there's a new packet. The coroutine is created when the filter is primed and will wait for input.

When input is recieved, the coroutine inspects the packet to decide if it's a message bottle or a data packet. If it's a message bottle and it is meant to be read by this filter, it will be opened and acted upon if recognised as a legitimate message. If it is not meant to be opened by this filter it is sent on via the :meth:`send_on` method. If it is a data packet, the the :meth:`filter_data` method is called and whatever functionality the filter is supposed to have is performed.

Pipes
-----

Pipeline Creation
-----------------

Configuration File Parsing
--------------------------
