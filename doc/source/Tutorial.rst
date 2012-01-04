.. _Tutorial:

Tutorial
========

This tutorial will help with the basic understanding of constructing Pipelines.

The first step in writing a Pipeline is to know what it is you want to achieve. What simple tasks need doing? What order do they need doing in? Are there existing Filters to accomplish these tasks or do I need to write them? Once a basic flow has been established and it is known which Filters are left to write (if any), then we can proceed.

An example problem to solve is: 'I need to take data from a file, break it up into 512 byte chunks, and count how many chunks there were.'

This is a very simple task to build a Pipeline for and the Filters already exist to do this. However, for the sake of this example we shall pretend that some of the Filters need to be written so that examples of how to do this can be shown.

.. NOTE:: All code samples used in this tutorial can be found under filterpype/tutorial.py and tests for them can be found in filterpype/tests/tutorial_test.py.

Writing the Pipeline configuration
----------------------------------

The first step is to know what needs to be done in order to achieve the end goal. To start off we obviously need to get the data! Without any data there is nothing to pass down the Pipeline. So the first part of our Pipeline is as follows:

.. code-block:: none
    :linenos:

    [--route--]
    read_batch

The [--route--] section header is the only required section for writing Pipeline configs. The read_batch line tells the parser that the first Filter in the Pype is read_batch.

The next step in this task is likely to be feeding it into a Filter that can break it into chunks:

.. code-block:: none
    :linenos:

    [--route--]
    read_batch >>>
    split_data:512

This is how our Pipeline config might now look. We have the read_batch and split_data Filters. The split_data Filter also has an argument. Arguments are appended after the Filter name and split up by colons. There may be multiple arguments and they must be in the order that the Filter is expecting them to be in, which is to say, the order in which the Filter has been written to accept them in.

There is another method in which arguments can be provided to Filters. Instead of writing the configuration as it appears above, it could also have been written like so:

.. code-block:: none
    :linenos:

    [--main--]

    [split_data]
    data_chunk_size = 512

    [--route--]
    read_batch >>>
    split_data

This has added a section for the filter that requires a key argument to be passed.

The last part of the pipeline is the chunk counter:

.. code-block:: none
    :linenos:

    [--route--]
    read_batch >>>
    split_data:512 >>>
    count_packets

Writing a Filter
----------------

In our example all we've done is write the configuration for the pipeline, but we haven't actually got all of the Filters in place to actually perform the real work. For the sake of the example lets pretend that we have both the read_batch and the count_packets Filters. What we want to do now is write the split_data Filter.

.. code-block:: python
    :linenos:

    class SplitData(dfb.DataFilter):
        ftype = 'split_data'
        description = 'Split data into 5 chunks, take the beginning of each chunk'+\
                    'up until block_size/5 and send on'
        keys = ['block_size']
    
        def filter_data(self, packet):
            #iterate through 5 equal chunks of the packet.data
            pkt_len = len(packet.data)
            for next_item in xrange(0, pkt_len, pkt_len/self.block_size):
                new_packet = packet.clone()
                new_packet.data = packet.data[next_item:next_item+(self.block_size/5)]
                self.send_on(new_packet)

The Filter itself is a class named :class:`SplitData` that inherits from :class:`DataFilter` which in turn inherits from the abstract class :class:`DataFilterBase`.

The :data:`ftype` is the name of the Filter and as you may have noticed, the name used when creating the Pipeline configuration.
The :data:`description = 'Split data into block_size chunks and send on sequentially'` line is required and should be a description of the Filter. 
The :data:`keys = ['block_size']` line will, during the creation of the Filter, end up making an object variable :data:`self.block_size` and will assign it the value 512, as we specified it to be in the configuration.

The :meth:`filter_data` method is the method in all Filters that does the actual work. Any number of other methods are allowed, just as would be expected in a Python class, but this one is the method that will be used to send packets to.
As can be seen the :meth:`data_filter` method is just looping through the packet data and splitting it into 512 byte chunks.

Line 9 show the start of a for loop. The point to note in this line is the len(packet.data) part. Packets which are data packets, all contain a :data:`data` attribute. This is where the data for the packet should be stored. The data is stored as a string but can be any data, not necessarily ASCII or unicode.

Line 10 shows a method belonging to the packet method: :meth:`packet.clone`. :meth:`packet.clone` is a method to clone the current packet. This means that the cloned packet will have an exact copy of all the attributes, keys, environment and data of the original packet. It is useful to clone a packet rather than create a new one as cloning ensures that no information will be lost.

Line 11 is assigning a subset of the original packets data to the new packet.

Line 12 shows the :meth:`self.send_on` method. This is the method to use to send on a packet to the next Filter in the Pipeline.

As filters are isolated from each other it is quite simple to write them. They are meant to be simple, one task, objects meaning that knowledge of how they are linked together is not needed in order to write them.

Creating a Pipeline
-------------------

Creating a Pipeline in Python is quite simple. Below is an example of a very simple Pipeline:

.. code-block:: python
    :linenos:

    import filterpype.pipeline as ppln

    class SplitDataPpln(ppln.Pipeline):
        config = '''
        [--main--]
        ftype = split_data_ppln
        description = Split the data 
        keys = block_size
    
        [split_data]
        block_size = ${block_size}
    
        [--route--]
        read_batch >>>
        split_data >>>
        sink
        '''
    
        def update_filters(self):
            self.getf('sink').max_results = 15

This example shows how to create a Pipeline using Python. The :class:`SplitData` class contains the config attribute that contains the Pipeline configuration.
There is also the :meth:`update_filters` method which allows the Filters to be updated with values when the Pipeline is first created. Update Filters is useful for updating
values in the Filters without requiring them to be input as Pipeline keys.

In order to use this Pipeline class it can be instantiated in Python as usual.

.. code-block:: python
    :linenos:

    pipeline2 = SplitData(factory=self.factory, data_chunk_size=1024)

Factories have been explained briefly in the _principles section. A typical factory might look like this:

.. code-block:: python
    :linenos:

    class TutorialFactory1(ff.FilterFactory):
        """ Factory Class """
    
        abstract_class = False
    
        def __init__(self):
            ff.FilterFactory.__init__(self)
            class_map = dict(
                read_batch = df.ReadBatch,
                sink = df.Sink,
                split_data = SplitData,
            )
    
            self._apply_class_map(class_map)

The class map maps ftypes to their Filter class references. The method :meth:`self._apply_class_map` is used
the mappings are made and the factory is ready to be used.

Each Pipeline needs a factory.

When instantiating Pipelines, any keys that are required by the Pipeline must also be passed in. In this case there is
one key that is required: :data:`data_chunk_size` which is set to 1024.

Extended Worked Example
-----------------------

Let's change the requirements of our Pipeline a bit.  
We want to split data in a packet in to chunks as before, but this time we want to write each 'split' to a separate file.
AND we want our Pipeline to write packets as well as leaving the original data intact - i.e. send on whatever is sent in.

Firstly, we need to analyse the problem.  We need a Filter that will split data in to chunks of a size defined by the user.
This Filter should be followed by another Filter to write these chunks to separate files - this file writer would need to have logic to change the name of the file written for each packet it received.
Finally, we would need another Filter to put the data back in to it's original format.

This is a dumb solution.  We can do better by using some advanced features of Pypes and Filters.

We already have a Filter that writes packets to files.  We also have a way of changing Filter keys during the execution of a Pipeline - through use of the Python environment.

A better solution would be to write a Filter that would send split packets to a branch and send on original packets to the main flow.
We could have a Python environment block on the branch that would change a global FILE_NAME variable; thus changing the file_name key in write_file.
Since the branch is executed first, we would be able to write our split packets here - using the generic write_file filter.

.. code-block:: python
    :linenos:

    class SplitDataBranchPipeline(ppln.Pipeline):        
        config = '''
        [--main--]
        ftype = split_data_branch_ppln
        description = 'Split packet.data in to block sizes defined by the user and write them out to seperate files'
        keys = data_chunk_size
        
        [split_branch]
        chunk_size = ${data_chunk_size}
        
        [py_change_file_name]
        print "Start of py section"
        try:
            FILE_NAME + ''
        except NameError:
            FILE_NAME = 'split_data_0'
        except TypeError:
            FILE_NAME = 'split_data_0'
    
        print FILE_NAME
        tokens = FILE_NAME.split('_')
        file_num = int(tokens[-1]) + 1
        new_tokens = tokens[:-1]
        new_tokens.append(str(file_num))
        FILE_NAME = '_'.join(new_tokens)
        print "End of py section"
        
        #[write_file]
        #dest_file_name = %FILE_NAME
        
        [--route--]
        read_batch >>>
        split_branch >>>
            (py_change_file_name >>>
            write_file:%FILE_NAME >>>
            waste)
        pass_through
        '''


.. code-block:: python
    :linenos:

    class SplitDataBranch(dfb.DataFilter):
        ftype = 'split_data_branch'
        description = 'Split data into chunks of size chunk_size'
        keys = ['chunk_size']
    
        def filter_data(self, packet):
            #iterate through 5 equal chunks of the packet.data
            pkt_len = len(packet.data)
            print "pkt_len:", pkt_len
            for next_item in xrange(0, pkt_len, pkt_len/self.chunk_size):
                new_packet = packet.clone()
                new_packet.data = packet.data[next_item:next_item+(self.chunk_size/5)]
                self.send_on(new_packet, 'branch')
            self.send_on(packet, 'main')
        
Are you getting a parsing error about '%' being an illegal character?  Try deleting parsetab.py and lextab.py.
