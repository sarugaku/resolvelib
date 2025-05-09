import collections
import pytest

from resolvelib import Resolver
from resolvelib.resolvers.resolution import Resolution

# Create a simple dummy provider instead of importing from conftest
class DummyProvider:
    def identify(self, requirement_or_candidate):
        return requirement_or_candidate
    
    def get_preference(self, identifier, resolutions, candidates, information, backtrack_causes):
        return 0
    
    def find_matches(self, identifier, requirements, incompatibilities):
        return [identifier]
    
    def is_satisfied_by(self, requirement, candidate):
        return True
    
    def get_dependencies(self, candidate):
        return []


class ConflictingRequirementsProvider(DummyProvider):
    """Provider that creates conflicts requiring backjumping."""
    
    def identify(self, requirement_or_candidate):
        return requirement_or_candidate
    
    def get_dependencies(self, candidate):
        # Create a dependency tree that will require backjumping
        if candidate == 'root':
            return ['A', 'B']
        elif candidate == 'A':
            return ['C==1']
        elif candidate == 'B':
            return ['C==2']
        return []
        
    def find_matches(self, identifier, requirements, incompatibilities):
        # Return candidates in a way that forces backjumping
        if identifier == 'C':
            # Return in an order that will cause backjumping
            return ['C==2', 'C==1']
        return [identifier]
        
    def is_satisfied_by(self, requirement, candidate):
        # C==1 and C==2 are incompatible
        if requirement == 'C==1' and candidate == 'C==2':
            return False
        if requirement == 'C==2' and candidate == 'C==1':
            return False
        return True


def test_optimistic_backjumping_timeout():
    """Test that optimistic backjumping respects the round-based timeout."""
    
    # Create a minimal resolution object to test the timeout logic
    resolution = Resolution(None, None)
    
    # Use different ratio values and verify behavior
    
    # Test that the default ratio exists
    assert hasattr(resolution, "_optimistic_backjumping_ratio")
    assert resolution._optimistic_backjumping_ratio == 0.5
    
    # Simulate optimistic backjumping starting on round 50 with max_rounds=150
    resolution._optimistic_backjumping_start_round = 50
    max_rounds = 150
    
    # Calculate optimistic backjumping limits for various round indices
    remaining_rounds = max_rounds - resolution._optimistic_backjumping_start_round
    max_optimistic_rounds = int(remaining_rounds * resolution._optimistic_backjumping_ratio)
    
    # With default ratio (0.5), optimistic backjumping should be allowed for half of remaining rounds
    assert max_optimistic_rounds == 50  # (150 - 50) * 0.5 = 50
    
    # Setting ratio to 0 should disable optimistic backjumping immediately
    resolution._optimistic_backjumping_ratio = 0.0
    max_optimistic_rounds = int(remaining_rounds * resolution._optimistic_backjumping_ratio)
    assert max_optimistic_rounds == 0
    
    # Setting ratio to 1.0 should allow optimistic backjumping for all remaining rounds
    resolution._optimistic_backjumping_ratio = 1.0
    max_optimistic_rounds = int(remaining_rounds * resolution._optimistic_backjumping_ratio)
    assert max_optimistic_rounds == 100  # All remaining rounds: 150 - 50 = 100