from avalon import api


def update_filesequence_instance(instance, start, end):
    """Update the instance's frame range and file collection

    Args:
        instance(pyblish.Instance): pyblish instance for publishing
        start (int): start frame
        end (int): end frame

    Returns:
        instance
    """

    original = "originalIndexes"
    collection = instance[0]

    # Before updating store the old frame range in the instance.
    # This will ensure the user to go back to the old range
    if original not in instance.data:
        instance.data[original] = list(collection.indexes)

    # Check if start and end frames are within frames
    indexes = instance.data[original]
    if start not in indexes:
        print("Cannot update outside of range of files")
        return

    if end not in indexes:
        print("Cannot update outside of range of files")
        return

    start_frame = start - 1  # we work from a list so -1 as it starts at 0
    new_indexes = indexes[start_frame:end]

    # Update collection range
    print("Updating frame range to {} : {}".format(start, end))
    collection.indexes.clear()
    collection.indexes.update(set(new_indexes))

    # Update instance data
    instance.data["startFrame"] = start
    instance.data["endFrame"] = end

    instance.data["name"] = str(collection)
    instance.data.pop("files", None)
    instance.data["files"] = [list(collection)]

    return instance


# Lazy functions
def get_project():
    """Lazy function to retrieve the current project"""
    return api.Session["AVALON_PROJECT"]


def get_silo():
    """Lazy function to retrieve the current silo"""
    return api.Session.get("AVALON_SILO", None)


def get_asset():
    """Lazy function to retrieve the current asset"""
    return api.Session.get("AVALON_ASSET", None)


def get_task():
    """Lazy function to retrieve the current task"""
    return api.Session.get("AVALON_TASK", None)
