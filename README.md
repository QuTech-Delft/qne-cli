# Quantum Network Explorer ADK

The QNE-ADK is a Quantum Network Explorer - Application Development Kit that allows you to create your own applications and experiments and run them on a simulator.

## Local development

With the ADK you can create your own application from scratch using the ``qne application create`` command
(see section 'Commands' below for more information about the individual commands). An application directory is created with all the necessary files for you to configure.
When configuring an application, you specify the different roles and what types of inputs your
application uses. In addition, you write the functionality of your application using the NetQASM library.

After creating and configuring an application, you can create an experiment for it using the ``qne experiment create``
command. A separate experiment directory is created with all the necessary files. When configuring your experiment
you can give values to the inputs that were specified when creating your application. You also choose which channels
and nodes you use in your network and which role is linked to which node. A network consists of channels and each
channel consists of two nodes. The nodes can communicate with each other using the channel between them.

Once your experiment is configured you are ready to run it using the ``qne experiment run`` command. Your experiment
is parsed and sent to the NetSquid simulator. After some time your experiment run will be finished and a results
directory will be generated in which all the results of your experiment are stored. An alternative is to use the
``qne experiment results`` command to show the results on screen.

## Publishing applications

When your application is finished and you want to share it with the world, an application can be uploaded and
published after which it can be selected by other users on the QNE platform. After uploading the application
``qne application upload`` a remote experiment must be created ``qne experiment create --remote`` and run
``qne experiment run`` first on the QNE simulator backend successfully before the application can be
published ``qne application publish``. After the application is published successfully, it can be used by others.
For commands interacting with the remote QNE server you must log in first ``qne login``.

Instead of starting from scratch an existing QNE application can be cloned using the ``qne application clone`` command.
A copy of a working application is made to your application directory and can be used as starting point
for application development.

## Prerequisites
- A modern Linux or macOS (10 or 11) 64-bit (x86_64) operating system. If you don’t have Linux or macOS you could run it via virtualization, e.g. using VirtualBox. If you have Windows 10 or 11 you can also use [Windows Subsystem for Linux](https://docs.microsoft.com/en-us/windows/wsl/).
- A [virtual environment](https://docs.python.org/3/library/venv.html) should be created and activated before creating an application.
- Python version 3.8 or higher.
- NetQASM makes use of SquidASM for which you need credentials in order to use it. These credentials can be obtained by registering on the forum of [NetSquid](https://forum.netsquid.org/).

## Installation
To install all the required packages, execute the following command:

```
pip install qne-adk
```

After installing the qne-adk, you can install [SquidASM](https://github.com/QuTech-Delft/squidasm). Replace `${NETSQUIDPYPI_USER}` and `${NETSQUIDPYPI_PWD}` with the username and password you registered on [NetSquid](https://forum.netsquid.org/):

```
pip install squidasm==0.12.1 --extra-index-url=https://${NETSQUIDPYPI_USER}:${NETSQUIDPYPI_PWD}@pypi.netsquid.org
```

Now everything should be setup and ready in order to create your own applications and experiments and run them on the simulator!

## Commands
The QNE-ADK uses various commands to create and run your applications and experiments. All the commands are listed below:

<!--- QNE APPLICATION LIST --->
<details closed>
<summary><b>qne application list</b></summary>
Show a list of all applications and relevant information for each of them.
For listing remote applications, the user must be logged in.
<br></br>

```
qne application list [OPTIONS]

Options:
  --remote  List remote applications  [default: False]
  --local   List local applications  [default: False].
  --help    Show this message and exit.

Example:
  qne application list --remote
```
</details>

<!--- QNE APPLICATION INIT --->
<details closed>
<summary><b>qne application init</b></summary>
Initialize an existing application in the current path which is not already registered to QNE-ADK.
This is needed for applications not created with QNE-ADK, for example when the files come from a
repository or are directly copied to the file system.
Two subdirectories <b>src</b> and <b>config</b> will be created when not already there.
When application files are in the root directory, but belong to one of the subdirectories, they are moved.
<br></br>

```
qne application init [OPTIONS] APPLICATION_NAME

  ./application_name is taken as application directory

Arguments:
  APPLICATION_NAME  Name of the application  [required]

Options:
  --help    Show this message and exit.

Example:
  qne application init application_name
```
</details>

<!--- QNE APPLICATION CREATE --->
<details closed>
<summary><b>qne application create</b></summary>
Create a new application in your current directory containing all the files that are needed to write your application.
The application directory name will be based on the value given to <b>application_name</b>.
Two subdirectories <b>src</b> and <b>config</b> will be created, along with the default files.
<br></br>

```
qne application create [OPTIONS] APPLICATION_NAME ROLES...

Arguments:
  APPLICATION_NAME  Name of the application  [required]
  ROLES...          Names of the roles to be created  [required]

Options:
  --help  Show this message and exit.

Example:
  qne application create my_application Alice Bob
```
</details>

<!--- QNE APPLICATION CLONE --->
<details closed>
<summary><b>qne application clone</b></summary>
Clone an existing remote or local application and use it as a starting point for new application development.
Cloning an application will copy the application files to the current directory.
The public available (or latest) version of the application is copied.
When a new application name is not given as an argument (remote only) the application will have the same name as
the cloned application. An application with the new application name may not already exist locally.
A local application must be valid before it can be cloned. For cloning a remote application the user must be logged in.
<br></br>

```
qne application clone [OPTIONS] APPLICATION_NAME [NEW_APPLICATION_NAME]

Arguments:
  APPLICATION_NAME        Name of the application to clone  [required]
  [NEW_APPLICATION_NAME]  New name for the cloned application

Options:
  --remote  Clone remote application  [default: False]
  --help    Show this message and exit.

Example:
  qne application clone existing_application new_application
```
</details>

<!--- QNE APPLICATION FETCH --->
<details closed>
<summary><b>qne application fetch</b></summary>
Fetching an existing remote application will copy the application files to the current directory.
The highest version of the application files are copied which may not be the current public version but a draft version.
Fetching applications is limited to the applications for which the user is the author.
For fetching a remote application the user must be logged in.
<br></br>

```
qne application fetch [OPTIONS] APPLICATION_NAME

Arguments:
  APPLICATION_NAME        Name of the application to fetch  [required]

Options:
  --help    Show this message and exit.

Example:
  qne application fetch existing_application
```
</details>

<!--- QNE APPLICATION DELETE --->
<details closed>
<summary><b>qne application delete</b></summary>
Delete the files of an application. Will try to delete the application directory
structure but keeps the files that are not part of the application.
For deleting remote parts of the application, the user must be logged in.
<br></br>

```
qne application delete [OPTIONS] [APPLICATION_NAME]

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
  qne application delete application_name
```
</details>

<!--- QNE APPLICATION VALIDATE --->
<details closed>
<summary><b>qne application validate</b></summary>
Validate the application created locally.
<br></br>

```
qne application validate [OPTIONS] [APPLICATION_NAME]

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
  qne application validate application_name
```
</details>

<!--- QNE APPLICATION UPLOAD --->
<details closed>
<summary><b>qne application upload</b></summary>
Create or update a remote application.
For creating or updating remote applications, the user must be logged in.
<br></br>

```
qne application upload [OPTIONS] [APPLICATION_NAME]

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
  qne application upload application_name
```
</details>

<!--- QNE APPLICATION PUBLISH --->
<details closed>
<summary><b>qne application publish</b></summary>
Request the application to be published online.
For publishing a new version of a remote application, the author of the application
must have run at least one successful experiment on the remote backend for the new
version of the application.
For publishing a new version of remote applications, the user must be logged in.
<br></br>

```
qne application publish [OPTIONS] [APPLICATION_NAME]

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
  qne application publish application_name
```
</details>

<!--- QNE EXPERIMENT LIST --->
<details closed>
<summary><b>qne experiment list</b></summary>
List remote experiments.
For listing remote experiments, the user must be logged in.
<br></br>

```
qne experiment list [OPTIONS]

Options:
  --help   Show this message and exit.

Example:
  qne experiment list
```
</details>

<!--- QNE EXPERIMENT CREATE --->
<details closed>
<summary><b>qne experiment create</b></summary>
Create a new experiment, based on an application name and a chosen network.
When the experiment is created for a remote application the user must be logged in.
<br></br>

```
qne experiment create [OPTIONS] EXPERIMENT_NAME APPLICATION_NAME NETWORK_NAME

Arguments:
  EXPERIMENT_NAME   Name of the experiment.  [required]
  APPLICATION_NAME  Name of the application.  [required]
  NETWORK_NAME      Name of the network to be used. [required]

Options:
  --remote  Use remote application configuration [default: False]
  --help    Show this message and exit.

Example:
  qne experiment create experiment_name application_name europe
```
</details>

<!--- QNE EXPERIMENT DELETE --->
<details closed>
<summary><b>qne experiment delete</b></summary>
Delete experiment files.
<br></br>

```
qne experiment delete [OPTIONS] [EXPERIMENT_NAME]

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
  --help    Show this message and exit.

Example:
  qne experiment delete experiment_name
```
</details>

<!--- QNE EXPERIMENT VALIDATE --->
<details closed>
<summary><b>qne experiment validate</b></summary>
Validate the local experiment.
<br></br>

```
qne experiment validate [OPTIONS] [EXPERIMENT_NAME]

  When experiment_name is given ./experiment_name is taken as experiment directory.
  When experiment_name is not given, the current directory is taken as experiment
  directory.

Arguments:
  [EXPERIMENT_NAME]  Name of the experiment

Options:
  --help  Show this message and exit.

Example:
  qne experiment validate experiment_name
```
</details>

<!--- QNE EXPERIMENT RUN --->
<details closed>
<summary><b>qne experiment run</b></summary>
This command will parse all experiment files and run them on the NetSquid simulator.
<br></br>

```
qne experiment run [OPTIONS] [EXPERIMENT_NAME]

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
  --block    Wait for the (remote) experiment to finish.  [default: False]
  --timeout  Limit the wait for a blocked experiment to finish (in seconds).
             [default: no timeout]
  --help     Show this message and exit.

Example:
  qne experiment run --block --timeout=30 experiment_name
```
</details>

<!--- QNE EXPERIMENT RESULTS --->
<details closed>
<summary><b>qne experiment results</b></summary>
Get results for an experiment that run successfully.
<br></br>

```
qne experiment results [OPTIONS] [EXPERIMENT_NAME]

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
  qne experiment results experiment_name
```
</details>

<!--- QNE LOGIN --->
<details closed>
<summary><b>qne login</b></summary>
Log in to a Quantum Network Explorer.
<br></br>

```
qne login [OPTIONS] [HOST]

Arguments:
  [HOST]  Name of the host to log in to

Options:
  --email TEXT     Email of the remote user  [required]
  --password TEXT  Password of the remote user  [required]
  --help           Show this message and exit.

Example:
  qne login --email=myemail@email.com --password=my_password https://api.quantum-network.com
```
</details>

<!--- QNE LOGOUT --->
<details closed>
<summary><b>qne logout</b></summary>
Log out from Quantum Network Explorer.
<br></br>

```
qne logout [OPTIONS] [HOST]

Arguments:
  [HOST]  Name of the host to log out from

Options:
  --help           Show this message and exit.

Example:
  qne logout https://api.quantum-network.com
```
</details>

<!--- QNE NETWORK LIST--->
<details closed>
<summary><b>qne network list</b></summary>
List available networks. For listing remote networks, the user must be logged in.
<br></br>

```
qne network list [OPTIONS]

Options:
  --remote  List remote networks  [default: False]
  --local   List local networks  [default: True]
  --help    Show this message and exit.

Example:
  qne network list --remote
```
</details>

<!--- QNE NETWORK UPDATE--->
<details closed>
<summary><b>qne network update</b></summary>
Get remote networks and update local network files.
For updating local networks, the user must be logged in.
<br></br>

```
qne network update [OPTIONS]

Options:
  --overwrite  Overwrite local networks  [default: False]
  --help       Show this message and exit.


Example:
  qne network update --overwrite
```
</details>

## More documentation
More documentation about these commands and about the files that are generated can be found in the QNE-ADK user guide on the Quantum Network Explorer [knowledge base](https://www.quantum-network.com/knowledge-base/qne-quantum-application-development-kit-adk/).
