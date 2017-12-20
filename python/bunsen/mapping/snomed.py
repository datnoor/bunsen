"""
Support for importing SNOMED relationship files into Bunsen.
"""

from bunsen.mapping import Hierarchies

def with_relationships(sparkSession, hierarchies, snomed_relationship_path, snomed_version):
    """
    Returns a hierarchies instance that includes the SNOMED relationships read
    from the given location.
    """
    snomed = sparkSession._jvm.com.cerner.bunsen.mappings.systems.Snomed

    jhierarchies = snomed.withRelationships(sparkSession._jsparkSession,
                                           hierarchies._jhierarchies,
                                           snomed_relationship_path,
                                           snomed_version)

    return Hierarchies(sparkSession, jhierarchies)
