"""This module contains the business logic of the function.

Use the automation_context module to wrap your function in an Autamate context helper
"""

import json
from pydantic import Field, SecretStr
from speckle_automate import (
    AutomateBase,
    AutomationContext,
    execute_automate_function,
)

import requests
import matplotlib.pyplot as plt
import matplotlib.patches as patches


class FunctionInputs(AutomateBase):
    """These are function author defined values.

    Automate will make sure to supply them matching the types specified here.
    Please use the pydantic model schema to define your inputs:
    https://docs.pydantic.dev/latest/usage/models/
    """
    # Username, Speckle token, API URL, token, and aspect ratio for shaft
    username: str = Field(title="Username")
    speckle_token: SecretStr = Field(title="Speckle token")
    api_url: SecretStr = Field(title="API URL")
    api_token: SecretStr = Field(title="API token")
    aspect_ratio: float = Field(title="Aspect ratio", default=2.0)


def automate_function(
    automate_context: AutomationContext,
    function_inputs: FunctionInputs,
) -> None:
    """This is an example Speckle Automate function.

    Args:
        automate_context: A context helper object, that carries relevant information
            about the runtime context of this function.
            It gives access to the Speckle project data, that triggered this run.
            It also has convenience methods attach result data to the Speckle model.
        function_inputs: An instance object matching the defined schema.
    """
    # Retrieve relevant context
    ard = automate_context.automation_run_data
    pl = automate_context.automation_run_data.triggers[0].payload

    # Setup data for request
    data = {
        'datafusr_config': {
            'project_name': 'MEPPostprocessingProject',
            'source_url': f"{ard.speckle_server_url}/projects/{ard.project_id}/models/{pl.model_id}@{pl.version_id}",
            'speckle_token': function_inputs.speckle_token.get_secret_value(),
        }
    }

    # Setup headers for request
    headers = {
        'content-type': 'application/json',
        'enable-logging': 'False',
        'source-application': 'RoomBook',
        'return-type': 'tables',
        'username': function_inputs.username,
        'token': function_inputs.api_token.get_secret_value(),
    }

    # Set URL
    url = f"{function_inputs.api_url.get_secret_value()}/from_datafusr/"

    # Make a POST request to the MEP API, dumping and loading the data to avoid JSON serialization issues
    response = requests.post(url, json=json.loads(json.dumps(data)), headers=headers).json()

    # Handle response
    if table := response.get('shaft_design'):

        try:

            # Plot cross-sections of each shaft using matplotlib
            for shaft_id in table.get('shaft_area', list()):

                if not table['shaft_area'][shaft_id]:
                    print(f'Shaft {shaft_id} has no area, skipping plot.')
                    continue

                # Shaft dimensions
                aspect_ratio = function_inputs.aspect_ratio
                shaft_width = (aspect_ratio * table['shaft_area'][shaft_id]) ** 0.5
                shaft_depth = shaft_width / aspect_ratio

                # Ventilation supply and return dimensions
                vent_supply_width = table['shaft_supply_width'][shaft_id] * 1E-3
                vent_supply_depth = table['shaft_supply_depth'][shaft_id] * 1E-3
                vent_return_width = table['shaft_return_width'][shaft_id] * 1E-3
                vent_return_depth = table['shaft_return_depth'][shaft_id] * 1E-3

                # Heating/Cooling, Electrical, Plumbing areas
                heating_cooling_width = heating_cooling_depth = table['shaft_heating_cooling_area'][shaft_id] ** 0.5
                electrical_width = electrical_depth = table['shaft_electrical_area'][shaft_id] ** 0.5
                plumbing_width = plumbing_depth = table['shaft_plumbing_area'][shaft_id] ** 0.5

                # Create figure and axis
                fig, ax = plt.subplots()

                # Draw the shaft
                shaft = patches.Rectangle((0, 0), shaft_width, shaft_depth,
                                          edgecolor='black', facecolor='gray', linewidth=2)
                ax.add_patch(shaft)
                labels = ['Shaft']

                # Draw the ventilation supply area
                if vent_supply_width > 0 and vent_supply_depth > 0:
                    if vent_supply_width > vent_supply_depth:
                        vent_supply = patches.Rectangle(
                            (0.02 * shaft_width, 0.02 * shaft_depth), vent_supply_width, vent_supply_depth,
                            edgecolor='tab:cyan', facecolor='tab:cyan', alpha=0.5, hatch='/', linewidth=1)
                    else:
                        vent_supply = patches.Rectangle(
                            (0.02 * shaft_width, 0.02 * shaft_depth), vent_supply_depth, vent_supply_width,
                            edgecolor='tab:cyan', facecolor='tab:cyan', alpha=0.5, hatch='/', linewidth=1)
                    ax.add_patch(vent_supply)
                    labels.append('V. Sup.')

                # Draw the ventilation return area
                if vent_return_width > 0 and vent_return_depth > 0:
                    if vent_return_width > vent_return_depth:
                        vent_return = patches.Rectangle(
                            (0.98 * shaft_width, 0.02 * shaft_depth), -vent_return_width, vent_return_depth,
                            edgecolor='tab:cyan', facecolor='tab:cyan', alpha=0.5, hatch='\\', linewidth=1)
                    else:
                        vent_return = patches.Rectangle(
                            (0.98 * shaft_width, 0.02 * shaft_depth), -vent_return_depth, vent_return_width,
                            edgecolor='tab:cyan', facecolor='tab:cyan', alpha=0.5, hatch="\\", linewidth=1)
                    ax.add_patch(vent_return)
                    labels.append('V. Ret.')

                # Draw the heating/cooling area
                if heating_cooling_width > 0 and heating_cooling_depth > 0:
                    heating_cooling = patches.Rectangle(
                        (0.02 * shaft_width, 0.98 * shaft_depth), heating_cooling_width, -heating_cooling_depth,
                        edgecolor='tab:purple', facecolor='tab:purple', alpha=0.5, linewidth=1)
                    ax.add_patch(heating_cooling)
                    labels.append('H/C')

                # Draw the electrical area
                if electrical_width > 0 and electrical_depth > 0:
                    electrical = patches.Rectangle(
                        (0.5 * shaft_width - electrical_width / 2, 0.98 * shaft_depth - electrical_depth),
                        electrical_width, electrical_depth,
                        edgecolor='tab:orange', facecolor='tab:orange', alpha=0.5, linewidth=1)
                    ax.add_patch(electrical)
                    labels.append('Elec.')

                # Draw the plumbing area
                if plumbing_width > 0 and plumbing_depth > 0:
                    plumbing = patches.Rectangle(
                        (0.98 * shaft_width, 0.98 * shaft_depth), -plumbing_width, -plumbing_depth,
                        edgecolor='tab:brown', facecolor='tab:brown', alpha=0.5, linewidth=1)
                    ax.add_patch(plumbing)
                    labels.append('Plum.')

                # Set the aspect of the plot to be equal
                ax.set_aspect('equal')

                # Set limits and labels
                margin = 0.1 * shaft_width
                ax.set_xlim(-margin, shaft_width + margin)
                ax.set_ylim(-margin, shaft_depth + margin)
                ax.set_xlabel('Shaft width')
                ax.set_ylabel('Shaft depth')
                ax.set_title(f'Shaft cross-section {shaft_id}')

                # Add legend
                plt.legend(labels, loc='lower right')

                # Show plot
                plt.savefig(f'{shaft_id}_cross_section.png')

                # Attach the plot to the Speckle model
                automate_context.store_file_result(f'{shaft_id}_cross_section.png')

            # Mark run as successful
            automate_context.mark_run_success("Shaft cross-sections successfully generated!")

        except Exception as e:

            # Mark run as failed
            automate_context.mark_run_failed(f"Automation failed: {e}")

    else:

        # Mark run as failed
        automate_context.mark_run_failed("Automation failed: No shaft data could be retrieved!")


def automate_function_without_inputs(automate_context: AutomationContext) -> None:
    """A function example without inputs.

    If your function does not need any input variables,
     besides what the automation context provides,
     the inputs argument can be omitted.
    """
    pass


# make sure to call the function with the executor
if __name__ == "__main__":
    # NOTE: always pass in the automate function by its reference, do not invoke it!

    # pass in the function reference with the inputs schema to the executor
    execute_automate_function(automate_function, FunctionInputs)

    # if the function has no arguments, the executor can handle it like so
    # execute_automate_function(automate_function_without_inputs)
