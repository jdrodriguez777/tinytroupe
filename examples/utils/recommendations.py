import pandas as pd
import ipywidgets as widgets
import sys
sys.path.insert(0, '..')

from tinytroupe.factory import TinyPersonFactory
from tinytroupe.extraction import ResultsExtractor
from tinytroupe.environment import TinyWorld

def get_widgets(category_list:list) -> dict:
    '''
    Returns the widgets to select the parameters: category, client specifications
    and number of agents.
    
    Args:
        category_list (list): Categories of the products.
        
    Returns:
        category_box (widgets.Dropdown): Categories box selector.
        client_factory_text (widgets.Text): Client specifications generation text.
        n_agents_slider (widgets.IntSlider): Number of agents slider.
    '''

    category_box = widgets.Dropdown(
        options=category_list,
        description='Category:',
        disabled=False)

    client_factory_text = widgets.Text(description='Client:', value='Random person.')
    n_agents_slider = widgets.IntSlider(description='Agents:', min=2, max=20, value=2)
    
    results = dict()
    results['category_box'] = category_box
    results['client_factory_text'] = client_factory_text
    results['n_agents_slider'] = n_agents_slider
    
    return results
    

def get_client_profile(client_text:str) -> str:
    '''
    Generates and returns the created client personal features.
    
    Args:
        client_text (str): Client specifications generation text.
        
    Returns:
        client_profile (str): Client personal features.
    '''

    print('GENERATING THE CLIENT ...\n')
    client_factory = TinyPersonFactory(client_text)
    client = client_factory.generate_people(1, verbose=True)[0]
    client_profile = str(client.to_json()['persona'])
    return client_profile


def get_recommendations(selected_df:pd.DataFrame, category:str, client_profile:str, n_agents:int) -> list:
    '''
    Creates the agents, starts the discussion and returns the product selection by each agent.
    
    Args:
        selected_df (pd.DataFrame):  DataFrame with columns title and description, for a chosen category.
        category (str): Chosen category.
        client_profile (str): Client personal features.
        n_agents (int): Number of agents. 
        
    Returns:
        choices (list): Product selection by each agent. Contains number of product and name.
    '''

    print('\nGENERATING THE AGENTS ...\n')
    factory = TinyPersonFactory(f'''
                            People with a broad and diverse range of personalities, interests, backgrounds and socioeconomic status.
                            Focus in particular:
                              - on financial aspects, ensuring we have both people with high and low income.
                              - on aesthetic aspects, ensuring we have people with different tastes.
                            Each of them must have knowledge and experience with {category}.
                            ''')
    agents = factory.generate_people(n_agents, verbose=True)
    world = TinyWorld('Focus group', agents)

    print('\n*** STEP 1: Brainstorming ***\n')
    step1 = get_problem_description(selected_df, category, client_profile)
    print(step1)
    world.broadcast(step1)
    world.run(1)

    print('\n*** STEP 2: Product selection ***\n')
    step2 = 'Makes its own decision about which product is best for the client. Select **ONLY** one.'
    
    for agent in agents:
        agent.listen_and_act(step2)

    print('\n*** STEP 3: Extract the selected product by agent ***\n')
    step3 = 'Find the product the agent chose. Extract the product number and name. Extract only ONE result.'
    extractor = ResultsExtractor()    
    
    choices =[]
    
    for agent in agents:
        res = extractor.extract_results_from_agent(agent,
                                        extraction_objective=step3,
                                        fields=['product_number', 'product_name'],
                                        fields_hints={'product_number': 'Must be an integer, not a string.'},
                                        verbose=True)
    
        choices.append(res)

    return choices
    

def get_problem_description(selected_df:pd.DataFrame, category:str, client_profile:str) -> str:
    '''
    Returns prompt of instructions to start the agents discussion.
    
    Args:
        selected_df (pd.DataFrame):  DataFrame with columns title and description, for a chosen category.
        category (str): Chosen category.
        client_profile (str): Client personal features.
        
    Returns:
        prompt (str): Instructions to start the agents discussion.
    '''
    
    prompt = f'''
    An e-commerce client is intending to buy a product from the category {category}.
    Our goal is to evaluate different products for the client, given the description of various products and the client's profile.
    
    The client's profile is shown in the following json format:    
    {client_profile}
    
    The name and description of each product are shown in the following json format:    
    '''
    
    prompt += '{'
    for index, row in selected_df.iterrows():
        prompt += f'''
            'product_{index + 1}':
            <<<<
                'name': '{row.title}',
                'description: '{row.description}'
            >>>>,
            
        '''
    prompt = prompt.replace('<<<<', '{').replace('>>>>', '}') + '}'
    prompt += f'''

    First, choose the product of your preference and
    try to defend why it is the best choice for the client.
    Please start the discussion in a discussion group now.
    Don't talk to the client. Talk only to the focus group.
    '''

    return prompt