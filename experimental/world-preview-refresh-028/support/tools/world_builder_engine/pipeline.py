"""Test-only selection/model spies; not a production layout pipeline."""
def latest_preview(*args,**kwargs):raise AssertionError('A synthetic selection must be injected')
class LocalModelClient:
 def generate(self,*args,**kwargs):raise AssertionError('No model generation in portable tests')
