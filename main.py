import json
from jira import JIRA
import os

def create_or_check_test_case_issue_type(jira, project_key):
    """
    Check for existing Test Case issue type or suggest manual creation.
    
    :param jira: JIRA client instance
    :param project_key: Project key to check
    :return: Issue type name
    """
    try:
        # Retrieve all issue types for the project
        issue_types = jira.issue_types()
        
        # Check for existing 'Test Case' or similar issue type
        for issue_type in issue_types:
            if issue_type.name.lower() in ['test case', 'test']:
                return issue_type.name
        
        # If no matching issue type found, provide guidance
        print("No 'Test Case' issue type found. Please manually create one in your Jira project.")
        return 'Task'  # Fallback to Task
    
    except Exception as e:
        print(f"Could not retrieve issue types: {e}")
        return 'Task'

def create_test_case_tracking_issues(config_path, json_file_path):
    """
    Create and track Jira issues for test cases with adaptive linking.
    
    :param config_path: Path to the JSON configuration file with Jira credentials
    :param json_file_path: Path to the JSON file containing test case data
    :return: Dictionary of created issues and their initial status
    """
    # Load Jira configuration
    with open(config_path, 'r') as config_file:
        config = json.load(config_file)
    
    # Load test case data
    with open(json_file_path, 'r') as test_file:
        test_cases = json.load(test_file)
    
    # Authenticate with Jira
    jira = JIRA(
        server=config['jira_server'],
        basic_auth=(config['username'], config['api_token'])
    )
    
    try:
        # Determine appropriate issue type
        test_case_type = create_or_check_test_case_issue_type(jira, config['project_key'])
        
        # Create Epic/Parent issue for test case collection
        epic_params = {
            'project': config['project_key'],
            'summary': 'Test Case Collection',
            'description': 'Tracking and managing all test cases for the project',
            'issuetype': {'name': 'Epic'}
        }
        epic = jira.create_issue(**epic_params)
        print(f"Test Case Collection Epic created: {epic.key}")
        
        # Track created test case issues
        created_issues = {}
        
        # Workflow for test case status
        workflows = {
            'Not Started': 'To Do',
            'In Progress': 'In Progress',
            'Passed': 'Done',
            'Failed': 'Blocked'
        }
        
        # Create issues for each test case
        for test_case in test_cases:
            issue_params = {
                'project': config['project_key'],
                'summary': f"Test Case: {test_case['name']}",
                'description': f"""Test Case Details:
- Test ID: {test_case.get('test_id', 'N/A')}
- Description: {test_case.get('description', 'No description')}
- Expected Outcome: {test_case.get('expected_outcome', 'N/A')}
- Priority: {test_case.get('priority', 'Medium')}
- Module: {test_case.get('module', 'Unassigned')}
- Actual Status: {test_case.get('status', 'Not Started')}

Test Steps:
{chr(10).join('- ' + step for step in test_case.get('test_steps', []))}
""",
                'issuetype': {'name': test_case_type},
                # Add parent directly for next-gen projects
                'parent': {'key': epic.key}
            }
            
            # Create the test case issue
            issue = jira.create_issue(**issue_params)
            
            # Transition issue to appropriate status
            current_status = test_case.get('status', 'Not Started')
            target_workflow_status = workflows.get(current_status, 'To Do')
            
            try:
                # Get available transitions
                transitions = jira.transitions(issue)
                
                # Find the right transition
                for t in transitions:
                    if target_workflow_status.lower() in t['name'].lower():
                        jira.transition_issue(issue, t['id'])
                        break
            except Exception as e:
                print(f"Could not update issue status: {e}")
            
            # Track the created issue
            created_issues[issue.key] = {
                'name': test_case['name'],
                'initial_status': current_status
            }
            
            print(f"Test Case Issue created: {issue.key}")
        
        return {
            'epic_key': epic.key,
            'created_issues': created_issues
        }
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def main():
    # Paths to configuration and input files
    config_path = 'jira_config.json'
    json_file_path = 'data.json'
    
    # Run the Jira test case tracking
    result = create_test_case_tracking_issues(config_path, json_file_path)
    
    if result:
        print("Jira test case issues created successfully!")
        print(f"Test Case Collection Epic: {result['epic_key']}")
        print("Created Test Case Issues:")
        for key, details in result['created_issues'].items():
            print(f"- {key}: {details['name']} (Initial Status: {details['initial_status']})")

if __name__ == '__main__':
    main()