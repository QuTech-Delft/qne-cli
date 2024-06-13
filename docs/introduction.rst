Introduction
============

The QNE-ADK is a Quantum Network Explorer - Application Development Kit that allows you to create your own applications
and experiments and run them on a simulator.

Local development
-----------------

With the ADK you can create your own application from scratch using the ``qne application create`` command
(see section 'Commands' below for more information about the individual commands). An application directory is created
with all the necessary files for you to configure.
When configuring an application, you specify the different roles and what types of inputs your
application uses. In addition, you write the functionality of your application using the NetQASM library.

After creating and configuring an application, you can create an experiment for it using the ``qne experiment create``
command. Also, here an experiment directory is generated with all necessary files. When configuring your experiment
you can give values to the inputs that were specified when creating your application. You also choose which channels
and nodes you use in your network and which role is linked to which node. A network consists of channels and each
channel consists of two nodes. The nodes can communicate with each other using the channel between them.

Once your experiment is configured you are ready to run it using the ``qne experiment run`` command. Your experiment
is parsed and sent to the NetSquid simulator. After some time your experiment run will be finished and a results
directory will be generated in which all the results of your experiment are stored. An alternative is to use the
``qne experiment results`` command to show the results on screen.

Publishing applications
-----------------------

When your application is finished and you want to share it with the world, an application can be uploaded and
published after which it can be selected by other users on the QNE platform. After uploading the application
``qne application upload`` a remote experiment must be created ``qne experiment create --remote`` and run
``qne experiment run`` first on the QNE simulator backend successfully before the application can be
published ``qne application publish``. After the application is published successfully, it can be used by others.
For commands interacting with the remote QNE server you must log in first ``qne login``.

Instead of starting from scratch an existing QNE application can be cloned using the ``qne application clone`` command.
A copy of a working application is made to your application directory and can be used as starting point
for application development.

Prerequisites
-------------

* A modern Linux or macOS (10 or 11) 64-bit (x86_64) operating system. If you don't have Linux or macOS you could run
  it via virtualization, e.g. using VirtualBox. If you have Windows 10 or 11 you can also use
  the `Bash on Ubuntu <https://docs.microsoft.com/en-us/windows/wsl/>`_ subsystem.
* A `virtual environment <https://docs.python.org/3/library/venv.html>`_ should be created and activated before
  creating an application.
* Python version 3.8 or higher.
* NetQASM makes use of SquidASM for which you need credentials in order to use it. These credentials can be obtained
  by registering on the forum of `NetSquid <https://forum.netsquid.org/>`_.

Installation
------------

To install all the required packages, execute the following command:

.. code-block:: console

    pip install qne-adk

After installing the qne-adk, you can install SquidASM. Replace '{netsquid-user-name}' and '{netsquid-password}' with
the credentials you registered on `NetSquid <https://forum.netsquid.org/>`_:

.. code-block:: console

    pip install squidasm --extra-index-url=https://{netsquid-user-name}:{netsquid-password}@pypi.netsquid.org

Now everything should be setup and ready in order to create your own applications and experiments and run them on
the simulator!

Installation from source
------------------------

The source for the QNE-ADK can also be found at Github. For the default installation execute:

.. code-block:: console

    git clone https://github.com/QuTech-Delft/qne-adk
    cd qne-adk
    pip install .

If you want to install for development, install with:

.. code-block:: console

    pip install -e .[dev]

*Note: installing for development will install packages that are needed to develop the QNE-ADK itself.*

Installing for generating documentation
---------------------------------------

To install the necessary packages to perform documentation activities for QNE-ADK do:

.. code-block:: console

    pip install -e .[rtd]

To build the 'readthedocs' documentation do:

.. code-block:: console

    cd docs
    make html

The documentation is then build in 'docs/_build/html' and can be viewed `here <index.html>`_.

Troubleshooting
---------------

If you have any issues installing SquidASM (e.g. it only seems to use version 0.0.1), check the following:

- Make sure you're using the latest version of `pip` (run: `python -m pip install --upgrade pip`)
- Check you're using a supported Python version `here <https://pypi.netsquid.org/netsquid/>`_. In the wheel filenames,
  cpXX indicates the version - so if you have Python 3.10, but there is no cp310 wheel, switch to a supported version
  of Python. Check the OS is also compatible.
- If `pydynaa` is failing, check the same as above `here <https://pypi.netsquid.org/pydynaa/>`_.
- For help with Python versions, check out `pyenv <https://github.com/pyenv/pyenv>`_. You should probably be
  using `virtualenv <https://virtualenv.pypa.io/en/latest/>`_
  or `venv <https://docs.python.org/3/library/venv.html>`_ too.

Commands
--------

The QNE-ADK uses various commands to create and run your applications and experiments. All commands are
listed below:

application list
^^^^^^^^^^^^^^^^

.. code-block:: console

    qne application list [OPTIONS]

Show a list of all applications and relevant information for each of them.
For listing remote applications, the user must be logged in.

    Options:
      --remote  List remote applications  [default: False]
      --local   List local applications  [default: False].
      --help   Show this message and exit.

Example:

.. code-block:: console

    qne application list --remote

application init
^^^^^^^^^^^^^^^^

.. code-block:: console

    qne application init [OPTIONS] APPLICATION_NAME

Initialize an existing application in the current path which is not already registered to QNE-ADK.
This is needed for applications not created with QNE-ADK, for example when the files come from a
repository or are directly copied to the file system.
Two subdirectories `src` and `config` will be created when not already there.
When application files are in the root directory, but belong to one of the subdirectories, they are moved.

    Arguments:
      APPLICATION_NAME  Name of the application [required]

    Options:
      --help   Show this message and exit.

Example:

.. code-block:: console

    qne application init application_name

application create
^^^^^^^^^^^^^^^^^^

.. code-block:: console

    qne application create [OPTIONS] APPLICATION_NAME ROLES...

Create a new application in your current directory containing all the files that are needed to write your application.
The application directory name will be based on the value given to `application_name`.
Two subdirectories `src` and `config` will be created, along with the default files.

    Arguments:
      APPLICATION_NAME  Name of the application [required]

      ROLES...          Names of the roles to be created [required]

    Options:
      --help  Show this message and exit.

Example:

.. code-block:: console

    qne application create my_application Alice Bob

application clone
^^^^^^^^^^^^^^^^^

.. code-block:: console

    qne application clone [OPTIONS] APPLICATION_NAME [NEW_APPLICATION_NAME]

Clone an existing remote or local application and use it as a starting point for new application development.
Cloning an application will copy the application files to the current directory.
The public available (or latest) version of the application is copied.
When a new application name is not given as an argument (remote only) the application will have the same name as
the cloned application. An application with the new application name may not already exist locally.
A local application must be valid before it can be cloned. For cloning a remote application the user must be logged in.

    Arguments:
      APPLICATION_NAME  Name of the application to clone [required]

      [NEW_APPLICATION_NAME]  New name for the cloned application

    Options:
      --remote  Clone remote application  [default: False]
      --help  Show this message and exit.

Example:

.. code-block:: console

    qne application clone existing_application new_application

application fetch
^^^^^^^^^^^^^^^^^

.. code-block:: console

    qne application fetch [OPTIONS] APPLICATION_NAME

Fetching an existing remote application will copy the application files to the current directory.
The highest version of the application files are copied which may not be the current public version but a draft version.
Fetching applications is limited to the applications for which the user is the author.
For fetching a remote application the user must be logged in.

    Arguments:
      APPLICATION_NAME  Name of the application to clone [required]

    Options:
      --help  Show this message and exit.

    Example:
      qne application fetch existing_application

application delete
^^^^^^^^^^^^^^^^^^

.. code-block:: console

    qne application delete [OPTIONS] [APPLICATION_NAME]

Delete the files of an application. Will try to delete the application directory
structure but keeps the files that are not part of the application.
For deleting remote parts of the application, the user must be logged in.

When application_name is given ./application_name is taken as application
directory, when this directory does not contain an application the
application directory is fetched from the application configuration. When
application_name is not given, the current directory is taken as
application directory.

    Arguments:
      [APPLICATION_NAME]  Name of the application

    Options:
      --help  Show this message and exit.

Example:

.. code-block:: console

    qne application delete application_name

application validate
^^^^^^^^^^^^^^^^^^^^

.. code-block:: console

    qne application validate [OPTIONS]

Validate the application created locally.

When application_name is given ./application_name is taken as application
directory, when this directory does not contain an application the
application directory is fetched from the application configuration. When
application_name is not given, the current directory is taken as
application directory.

    Options:
      --help  Show this message and exit.

Example:

.. code-block:: console

    qne application validate

application upload
^^^^^^^^^^^^^^^^^^

.. code-block:: console

    qne application upload [OPTIONS] [APPLICATION_NAME]

Create or update a remote application.
For creating or updating remote applications, the user must be logged in.

When application_name is given ./application_name is taken as application
directory, when this directory does not contain an application the
application directory is fetched from the application configuration. When
application_name is not given, the current directory is taken as
application directory.

    Arguments:
      [APPLICATION_NAME]  Name of the application

    Options:
      --help   Show this message and exit.

Example:

.. code-block:: console

    qne application upload application_name

application publish
^^^^^^^^^^^^^^^^^^^

.. code-block:: console

    qne application publish [OPTIONS] [APPLICATION_NAME]

Request the application to be published online.
For publishing a new version of a remote application, the author of the application
must have run at least one successful experiment on the remote backend for the new
version of the application.
For publishing a new version of remote applications, the user must be logged in.

When application_name is given ./application_name is taken as application
directory, when this directory does not contain an application the
application directory is fetched from the application configuration. When
application_name is not given, the current directory is taken as
application directory.

    Arguments:
      [APPLICATION_NAME]  Name of the application

    Options:
      --help   Show this message and exit.

Example:

.. code-block:: console

    qne application publish application_name

experiment list
^^^^^^^^^^^^^^^

.. code-block:: console

    qne experiment list [OPTIONS]

List remote experiments.
For listing remote experiments, the user must be logged in.

    Options:
      --help   Show this message and exit.

Example:

.. code-block:: console

    qne experiment list

experiment create
^^^^^^^^^^^^^^^^^

.. code-block:: console

    qne experiment create [OPTIONS] EXPERIMENT_NAME APPLICATION_NAME NETWORK_NAME

Create a new experiment, based on an application name and a chosen network.
When the experiment is created for a remote application the user must be logged in.

    Arguments:
      EXPERIMENT_NAME   Name of the experiment.  [required]

      APPLICATION_NAME  Name of the application.  [required]

      NETWORK_NAME      Name of the network to be used. [required]

    Options:
      --remote  Use remote application configuration [default: False]
      --help   Show this message and exit.

Example:

.. code-block:: console

    qne experiment create experiment_name application_name europe

experiment delete
^^^^^^^^^^^^^^^^^

.. code-block:: console

    qne experiment delete [OPTIONS] [EXPERIMENT_NAME]

Delete experiment files.

Local: When deleting an experiment locally, argument EXPERIMENT_NAME_OR_ID
is the local experiment name, which is the subdirectory containing the
experiment files. When the argument is empty the current directory is
taken as experiment directory. The local experiment files are deleted,
when the experiment was created with '--remote' and the experiment was run
remotely, the remote experiment is also deleted.

Remote: the argument EXPERIMENT_NAME_OR_ID is the remote experiment id to
delete. No local files are deleted.

    Arguments:
      [EXPERIMENT_NAME_OR_ID]  Name of the experiment or remote id

    Options:
      --remote  Delete a remote experiment  [default: False]
      --help  Show this message and exit.

Example:

.. code-block:: console

    qne experiment delete experiment_name

experiment validate
^^^^^^^^^^^^^^^^^^^

.. code-block:: console

    qne experiment validate [OPTIONS] [EXPERIMENT_NAME]

Validate the local experiment.

When experiment_name is given ./experiment_name is taken as experiment directory.
When experiment_name is not given, the current directory is taken as experiment
directory.

    Arguments:
      [EXPERIMENT_NAME]  Name of the experiment

    Options:
      --help  Show this message and exit.

Example:

.. code-block:: console

    qne experiment validate experiment_name

experiment run
^^^^^^^^^^^^^^

.. code-block:: console

    qne experiment run [OPTIONS] [EXPERIMENT_NAME]

This command will parse all experiment files and run them on the NetSquid simulator.

When experiment_name is given ./experiment_name is taken as experiment directory.
When experiment_name is not given, the current directory is taken as experiment
directory.
Block (remote experiment runs only) waits for the experiment to finish before
returning (and results are available). Local experiment runs are blocked by default.
Timeout (optional) limits the wait (in seconds) for a blocked experiment to finish.
In case of a local experiment, a timeout will cancel the experiment run. A remote
experiment run is not canceled after a timeout and results can be fetched at a later
moment.

    Arguments:
      [EXPERIMENT_NAME]  Name of the experiment

    Options:
      --block  Wait for the (remote) experiment to finish.  [default: False]
      --timeout  Limit the wait for a blocked experiment to finish (in seconds).  [default: no timeout]
      --help   Show this message and exit.

Example:

.. code-block:: console

    qne experiment run --block --timeout=30 experiment_name

experiment results
^^^^^^^^^^^^^^^^^^

.. code-block:: console

    qne experiment results [OPTIONS] [EXPERIMENT_NAME]

Get results for an experiment that run successfully.

When experiment_name is given ./experiment_name is taken as experiment directory.
When experiment_name is not given, the current directory is taken as experiment
directory.

    Arguments:
      [EXPERIMENT_NAME]  Name of the experiment

    Options:
      --all   Get all results for this experiment.  [default: False]
      --show  Show the results on screen instead of saving to file.  [default:
              False]
      --help  Show this message and exit.

Example:

.. code-block:: console

    qne experiment results experiment_name

login
^^^^^

.. code-block:: console

    qne login [OPTIONS] [HOST]

Log in to a Quantum Network Explorer.

    Arguments:
      [HOST]  Name of the host to log in to

    Options:
      --email  TEXT Email of the remote user  [required]
      --password  TEXT Password of the remote user  [required]
      --help  Show this message and exit.

Example:

.. code-block:: console

    qne login --email=myemail@email.com --password=my_password https://api.quantum-network.com

logout
^^^^^^

.. code-block:: console

    qne logout [OPTIONS] [HOST]

Log out from Quantum Network Explorer.

    Arguments:
      [HOST]  Name of the host to log out from

    Options:
      --help  Show this message and exit.

Example:

.. code-block:: console

    qne logout https://api.quantum-network.com

network list
^^^^^^^^^^^^

.. code-block:: console

    qne network list [OPTIONS]

List available networks. For listing remote networks, the user must be logged in.

    Options:
      --remote  List remote networks  [default: False]
      --local   List local networks  [default: True]
      --help  Show this message and exit.

Example:

.. code-block:: console

    qne network list --remote

network update
^^^^^^^^^^^^^^

.. code-block:: console

    qne network update [OPTIONS]

Get remote networks and update local network files.
For updating local networks, the user must be logged in.

    Options:
      --overwrite  Overwrite local networks  [default: False]
      --help  Show this message and exit.

Example:

.. code-block:: console

    qne network update --overwrite

More documentation
------------------

Following this step-by-step documentation, it will give you a better understanding of:

* what each command implies
* which files are generated and their purpose
* a better understanding of what a quantum network consists of
* how to create and run your own applications and experiments

Bug reports
-----------

Please submit bug-reports `on the github issue
tracker <https://github.com/QuTech-Delft/qne-adk/issues>`_.
