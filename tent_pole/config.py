def user_config_dir(appname, roaming=True):
    """Return full path to the user-specific config dir for this application.

        "appname" is the name of application.
            If None, just the system directory is returned.
        "roaming" (boolean, default True) can be set False to not use the
            Windows roaming appdata directory. That means that for users on a
            Windows network setup for roaming profiles, this user data will be
            sync'd on login. See
            <http://technet.microsoft.com/en-us/library/cc766489(WS.10).aspx>
            for a discussion of issues.

    Typical user data directories are:
        macOS:                  same as user_data_dir
        Unix:                   ~/.config/<AppName>
        Win *:                  same as user_data_dir

    For Unix, we follow the XDG spec and support $XDG_CONFIG_HOME.
    That means, by default "~/.config/<AppName>".
    """
    if WINDOWS:
        path = user_data_dir(appname, roaming=roaming)
    elif sys.platform == "darwin":
        path = user_data_dir(appname)
    else:
        path = os.getenv("XDG_CONFIG_HOME", expanduser("~/.config"))
        path = os.path.join(path, appname)

    return path
