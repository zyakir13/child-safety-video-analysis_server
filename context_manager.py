class ContextManager:
    """Manages scene context chaining between frame sequences for improved AI analysis"""
    
    def __init__(self):
        self.context_history = []
        self.max_context_length = 3  # Keep last 3 scene contexts
    
    def add_scene_context(self, scene_context, timestamp_range):
        """Add a new scene context to the history"""
        if scene_context and scene_context.strip():
            context_entry = {
                'context': scene_context.strip(),
                'timestamp_range': timestamp_range,
                'sequence_number': len(self.context_history) + 1
            }
            
            self.context_history.append(context_entry)
            
            # Keep only the most recent contexts to avoid prompt bloat
            if len(self.context_history) > self.max_context_length:
                self.context_history = self.context_history[-self.max_context_length:]
            
            print(f"         Added scene context: '{scene_context[:50]}...'")
    
    def get_context_prompt_addition(self):
        """Generate context prompt addition for the next frame sequence"""
        if not self.context_history:
            return ""
        
        context_text = "\nPREVIOUS SCENE CONTEXT (for continuity):"
        
        for entry in self.context_history:
            timestamp_info = f"{entry['timestamp_range']['start']:.1f}s-{entry['timestamp_range']['end']:.1f}s"
            context_text += f"\n- Sequence {entry['sequence_number']} ({timestamp_info}): {entry['context']}"
        
        context_text += "\n\nUse this context to better understand the ongoing situation and identify any concerning developments or patterns.\n"
        
        print(f"         Providing context from {len(self.context_history)} previous sequences")
        
        return context_text
    
    def clear_context(self):
        """Clear all context history (for new video analysis)"""
        self.context_history = []
        print("         Context history cleared")
    
    def get_context_summary(self):
        """Get a summary of current context for debugging"""
        if not self.context_history:
            return "No context history"
        
        total_sequences = len(self.context_history)
        latest_context = self.context_history[-1]['context'][:100] + "..." if len(self.context_history[-1]['context']) > 100 else self.context_history[-1]['context']
        
        return f"{total_sequences} sequences in context. Latest: '{latest_context}'"

if __name__ == "__main__":
    # Test context manager
    manager = ContextManager()
    
    # Simulate adding contexts
    manager.add_scene_context("Children playing on couch in living room", {"start": 10.0, "end": 14.0})
    manager.add_scene_context("One child appears to be in distress while other child nearby", {"start": 14.0, "end": 18.0})
    
    print("\nContext prompt addition:")
    print(manager.get_context_prompt_addition())
    
    print(f"\nContext summary: {manager.get_context_summary()}")