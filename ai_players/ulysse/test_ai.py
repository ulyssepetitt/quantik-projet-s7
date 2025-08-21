#!/usr/bin/env python3
"""Test script for debugging the AI"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.types import Player, Shape
from core.rules import QuantikBoard
from ai_players.ulysse.algorithme import QuantikAI
import time

def create_empty_pieces_count():
    """Create initial pieces count"""
    return {
        Player.PLAYER1: {shape: 2 for shape in Shape},
        Player.PLAYER2: {shape: 2 for shape in Shape}
    }

def test_basic_ai():
    """Test basic AI functionality"""
    print("Testing AI basic functionality...")
    
    # Create AI
    ai = QuantikAI(Player.PLAYER1)
    
    # Create empty board
    board = [[None for _ in range(4)] for _ in range(4)]
    pieces_count = create_empty_pieces_count()
    
    print("Board state:")
    for row in board:
        print([str(cell) if cell else "." for cell in row])
    
    print(f"Pieces count: {pieces_count}")
    
    # Test first move
    print("Getting first move...")
    start_time = time.time()
    
    try:
        move = ai.get_move(board, pieces_count)
        end_time = time.time()
        
        print(f"AI move: {move}")
        print(f"Time taken: {end_time - start_time:.2f}s")
        
        if move is None:
            print("ERROR: AI returned None!")
            return False
            
        row, col, shape = move
        print(f"AI wants to play {shape} at ({row}, {col})")
        
    except Exception as e:
        print(f"ERROR: Exception during AI move: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def test_with_some_moves():
    """Test AI with some moves already played"""
    print("\nTesting AI with some moves played...")
    
    ai = QuantikAI(Player.PLAYER2)
    
    # Create board with some moves
    from core.types import Piece
    board = [[None for _ in range(4)] for _ in range(4)]
    board[0][0] = Piece(Shape.CIRCLE, Player.PLAYER1)
    board[1][1] = Piece(Shape.SQUARE, Player.PLAYER1)
    
    pieces_count = create_empty_pieces_count()
    pieces_count[Player.PLAYER1][Shape.CIRCLE] -= 1
    pieces_count[Player.PLAYER1][Shape.SQUARE] -= 1
    
    print("Board state:")
    for i, row in enumerate(board):
        print(f"Row {i}: {[str(cell) if cell else '.' for cell in row]}")
    
    try:
        start_time = time.time()
        move = ai.get_move(board, pieces_count)
        end_time = time.time()
        
        print(f"AI move: {move}")
        print(f"Time taken: {end_time - start_time:.2f}s")
        
        if move is None:
            print("ERROR: AI returned None!")
            return False
            
    except Exception as e:
        print(f"ERROR: Exception during AI move: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    print("=== AI Debug Test ===")
    
    success1 = test_basic_ai()
    success2 = test_with_some_moves()
    
    if success1 and success2:
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Some tests failed!")