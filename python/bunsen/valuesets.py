"""
Support for broadcasting valuesets and using them in user-defined functions
in Spark queries.
"""

from collections import namedtuple

from bunsen.mapping import get_default_value_sets, get_default_hierarchies

# Placeholder record to load a particular value set
ValueSetPlaceholder = namedtuple("ValueSetPlaceholder",
                                 "valueSetUri valueSetVersion")

# Placeholder record to load a particular hierarchical system
HierarchyPlaceholder = namedtuple("HierarchyPlaceholder",
                                  "codeSystem codeValue hierarchyUri hierarchyVersion")

def isa_loinc(code_value, loinc_version=None):
    """
    Returns a hierarchy placeholder that will load all values that are descendents
    of a given LOINC code.
    """
    return HierarchyPlaceholder('http://loinc.org',
                                code_value,
                                'urn:com:cerner:bunsen:hierarchy:loinc',
                                loinc_version)

def isa_snomed(code_value, snomed_version=None):
    """
    Returns a hierarchy placeholder that will load all values that are descendents
    of a given SNOMED code.
    """
    return HierarchyPlaceholder('http://snomed.info/sct',
                                code_value,
                                'urn:com:cerner:bunsen:hierarchy:snomed',
                                snomed_version)

def push_valuesets(spark_session, valueset_map, value_sets=None, hierarchies=None):
    """
    Pushes valuesets onto a stack and registers an in_valueset user-defined function
    that uses this content.

    The valueset_map takes the form of {referenceName: [(codeset, codevalue), (codeset, codevalue)]}
    to specify which codesets/values are used for the given valueset reference name.

    Rather than explicitly passing a list of (codeset, codevalue) tuples, users may instead
    load particular value sets or particular hierarchies by providing a ValueSetPlaceholder
    or HierarchyPlaceholder that instructs the system to load codes belonging to a particular
    value set or hierarchical system, respectively. See the isa_loinc and isa_snomed functions
    above for details.
    """
    if value_sets is None:
        value_sets = get_default_value_sets(spark_session)

    if hierarchies is None:
        hierarchies = get_default_hierarchies(spark_session)

    jvm = spark_session._jvm

    builder = jvm.com.cerner.bunsen.mappings.broadcast.BroadcastableValueSets.newBuilder()

    for (name, content) in valueset_map.items():

        print(name)
        print(content)

        if type(content) is HierarchyPlaceholder:

            # Add codes belonging to the specified hierarchy
            (codeSystem, codeValue, hierarchyUri, hierarchyVersion) = content

            builder.addDescendantsOf(name,
                                     codeSystem,
                                     codeValue,
                                     hierarchyUri,
                                     hierarchyVersion)

        elif type(content) is ValueSetPlaceholder:

            # Add codes belonging to the specified value set
            (valueSetUri, valueSetVersion) = content

            builder.addReference(name, valueSetUri, valueSetVersion)

        else:

            # Add the explicitly provided code values
            for (codeSystem, codeValue) in content:
                builder.addCode(name, codeSystem, codeValue)

    broadcastable = builder.build(spark_session._jsparkSession,
                                  value_sets._jvalue_sets,
                                  hierarchies._jhierarchies)

    jvm.com.cerner.bunsen.ValueSetUdfs.pushUdf(spark_session._jsparkSession, broadcastable)

def get_current_valuesets(spark_session):
    """
    Returns the current valuesets in the same form that is accepted by
    the push_valuesets function above, that is the structure will follow this pattern:
    {referenceName: [(codeset, codevalue), (codeset, codevalue)]}
    """
    jvm = spark_session._jvm

    current = jvm.com.cerner.bunsen.ValueSetUdfs.currentValueSets()

    if current is None:
        return None
    else:
        valuesets = current.getValue()

        return {name: [(system, value)
                       for system in valuesets.getValues(name).keySet()
                       for value in valuesets.getValues(name).get(system)]
                for name in valuesets.getReferenceNames()}

def pop_valuesets(spark_session):
    """
    Pops the current valuesets from the stack, returning true if there remains
    an active valueset, or false otherwise.
    """
    jvm = spark_session._jvm

    return jvm.com.cerner.bunsen.ValueSetUdfs.popUdf(spark_session._jsparkSession)
