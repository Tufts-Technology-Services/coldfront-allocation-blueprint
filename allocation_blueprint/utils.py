import re
from coldfront.core.project.models import ProjectAttribute
from coldfront.core.resource.models import ResourceAttribute 
from coldfront.core.allocation.models import Allocation


def render_template_string(template_string, context=None):
    """
    Renders a template string with the given context.
    This utility function uses Django's template engine to render a string as a template.

    :param template_string: The template string to render.
    :param context: A dictionary of context variables to use in the template.
    :return: The rendered template as a string.
    """
    return template_string.format(**context)


def get_context(template_string, allocation_id):
    matches = re.findall(r'\{(.*?)\}', template_string)
    context = {}
    for match in matches:
        context[match] = parse_context_reference(match, allocation_id)
    return context


def parse_context_reference(reference, allocation_id):
    """
    Parses a context reference in the format 'model.attribute' and retrieves the corresponding value.
    The model can be 'project' or 'resource', and the attribute is the name of the attribute to retrieve.
     :param reference: The context reference string to parse.
    :param allocation_id: The ID of the allocation for which to retrieve the context.
    :return: The value of the referenced attribute."""
    reference_parts = reference.split('.')
    if len(reference_parts) < 2:
        raise ValueError(f"Invalid context reference: {reference}. Expected format 'model.attribute'.")
    if len(reference_parts) > 2:
        raise ValueError(f"Invalid context reference: {reference}. Expected format 'model.attribute', but got more than one dot.")
    model_name = reference_parts[0].strip().lower()
    attribute_name = reference_parts[1].strip().strip('"').strip("'")
    if model_name not in ['project', 'resource']:
        raise ValueError(f"Invalid model name in context reference: {model_name}. Expected 'project' or 'resource'.")
    allocation = Allocation.objects.get(id=allocation_id)
    if model_name == 'project':
        attribute_match = ProjectAttribute.objects.filter(project=allocation.project, proj_attr_type__name__iexact=attribute_name)
        if not attribute_match.exists():
            raise ValueError(f"Project attribute '{attribute_name}' not found for project '{allocation.project.name}'.")
        return attribute_match.first().value
    elif model_name == 'resource':
        attribute_match = ResourceAttribute.objects.filter(resource=allocation.get_parent_resource, resource_attribute_type__name__iexact=attribute_name)
        if not attribute_match.exists():
            raise ValueError(f"Resource attribute '{attribute_name}' not found for resource '{allocation.get_parent_resource.name}'.")
        return attribute_match.first().value


def get_attribute_value(allocation_id, attribute_blueprint_value):
    """
    Retrieves the value for an allocation attribute based on the provided blueprint.
    If the blueprint value contains template variables, it renders the template using the allocation context.

    :param allocation_id: The ID of the allocation for which to retrieve the attribute value.
    :param attribute_blueprint_value: The blueprint value defining the attribute and its value template.
    :return: The rendered attribute value as a string.
    """
    if '{' in attribute_blueprint_value and '}' in attribute_blueprint_value:
        context = get_context(attribute_blueprint_value, allocation_id)
        return render_template_string(attribute_blueprint_value, context)
    else:
        return attribute_blueprint_value