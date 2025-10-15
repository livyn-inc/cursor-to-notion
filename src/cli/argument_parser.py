#!/usr/bin/env python3

"""
CLI argument parser for nit command
"""

import argparse
from typing import Any, Dict


def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser for nit CLI (v2.1)"""
    parser = argparse.ArgumentParser(
        prog='nit',
        description='Notion Integration Tool v2.1 - Sync local files with Notion pages',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  nit init <folder> --workspace-url <url>   # Initialize with workspace URL
  nit init <folder> --root-url <url>        # Initialize with project URL (legacy)
  nit clone <url> <folder>                  # Clone existing Notion pages
  nit push <folder>                         # Push local changes to Notion (changed files only)
  nit pull <folder>                         # Pull changes from Notion (new + changed pages)
  nit status <folder>                       # Show sync status

Options:
  nit push <folder> --force-all        # Force push all files
  nit pull <folder> --new-only         # Pull new pages only
  nit pull <folder> --existing-only    # Pull changed pages only
  nit push <folder> --dry-run          # Preview push without executing
  nit status <folder> --fix            # Auto-fix URL configuration issues
        """
    )
    
    subparsers = parser.add_subparsers(dest='cmd', help='Available commands')
    
    # ========================================
    # init command (v2.1: --workspace-url + interactive prompt)
    # ========================================
    init_parser = subparsers.add_parser('init', help='Initialize a folder for Notion sync')
    init_parser.add_argument('folder', nargs='?', help='Folder to initialize (interactive if not provided)')
    init_parser.add_argument('--workspace-url', help='Notion workspace URL (parent of project folder, interactive if not provided)')
    init_parser.add_argument('--root-url', help='[Legacy] Notion project page URL (for backward compatibility)')
    
    # ========================================
    # push command (v2.0: simplified options)
    # ========================================
    push_parser = subparsers.add_parser('push', help='Push local changes to Notion')
    push_parser.add_argument('folder', help='Folder to push')
    push_parser.add_argument('--force-all', action='store_true', 
                           help='Force push all files (ignore change detection)')
    push_parser.add_argument('--dry-run', action='store_true',
                           help='Preview changes without pushing')
    push_parser.add_argument('--verbose', action='store_true',
                           help='Show detailed logs')
    
    # ========================================
    # pull command (v2.0: simplified options)
    # ========================================
    pull_parser = subparsers.add_parser('pull', help='Pull changes from Notion')
    pull_parser.add_argument('folder', help='Folder to pull')
    pull_parser.add_argument('--new-only', action='store_true',
                           help='Only pull new pages (ignore existing page changes)')
    pull_parser.add_argument('--existing-only', action='store_true',
                           help='Only pull changed pages (ignore new pages)')
    pull_parser.add_argument('--dry-run', action='store_true',
                           help='Preview changes without pulling')
    pull_parser.add_argument('--verbose', action='store_true',
                           help='Show detailed logs')
    
    # ========================================
    # clone command (v2.1: --workspace-url, interactive prompt)
    # ========================================
    clone_parser = subparsers.add_parser('clone', help='Clone existing Notion pages')
    clone_parser.add_argument('notion_url', nargs='?', help='Notion project page URL (interactive if not provided)')
    clone_parser.add_argument('local_folder', nargs='?', help='Local folder path (interactive if not provided)')
    clone_parser.add_argument('--workspace-url', help='Notion workspace URL (auto-detected if not provided)')
    clone_parser.add_argument('--verbose', action='store_true',
                             help='Show detailed logs')
    
    # ========================================
    # status command (v2.0: --fix option added)
    # ========================================
    status_parser = subparsers.add_parser('status', help='Show project sync status')
    status_parser.add_argument('folder', help='Folder to analyze')
    status_parser.add_argument('--fix', action='store_true',
                             help='Auto-fix configuration issues')
    
    # ========================================
    # Legacy repo subcommands (backward compatibility)
    # ========================================
    repo_parser = subparsers.add_parser('repo', help='Repository management commands (legacy)')
    repo_subparsers = repo_parser.add_subparsers(dest='repo_cmd', help='Repository commands')
    
    # repo create
    repo_create_parser = repo_subparsers.add_parser('create', help='Create new repository')
    repo_create_parser.add_argument('name', help='Repository name')
    repo_create_parser.add_argument('--dir', default='.', help='Base directory (default: current)')
    repo_create_parser.add_argument('--parent-url', required=True, help='Parent Notion page URL')
    
    # repo clone (legacy, redirect to main clone)
    repo_clone_parser = repo_subparsers.add_parser('clone', help='Clone repository (use "nit clone" instead)')
    repo_clone_parser.add_argument('root_page_url', help='Root Notion page URL')
    repo_clone_parser.add_argument('--name', help='Folder name (default: page title)')
    repo_clone_parser.add_argument('--dir', default='.', help='Base directory (default: current)')
    
    return parser


def parse_args() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = create_argument_parser()
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    """Validate parsed arguments (v2.0)"""
    if not args.cmd:
        raise ValueError("No command specified. Use 'nit --help' for usage information.")
    
    # Validate folder paths for commands that require them
    # Note: init and clone allow interactive prompts, so folder might not exist yet
    folder_commands = ['push', 'pull', 'status']
    if args.cmd in folder_commands:
        import os
        folder = getattr(args, 'folder', None)
        if folder and not os.path.exists(folder):
            raise ValueError(f"Folder does not exist: {folder}")
        if folder and not os.path.isdir(folder):
            raise ValueError(f"Path is not a directory: {folder}")
    
    # Validate mutually exclusive options for pull
    if args.cmd == 'pull':
        if getattr(args, 'new_only', False) and getattr(args, 'existing_only', False):
            raise ValueError("--new-only と --existing-only は同時に指定できません")


def get_command_config(args: argparse.Namespace) -> Dict[str, Any]:
    """Extract command configuration from parsed arguments (v2.1)"""
    config = {
        'command': args.cmd,
        'folder': getattr(args, 'folder', None),
        'verbose': getattr(args, 'verbose', False),
    }
    
    # Command-specific options (v2.1: workspace_url support)
    if args.cmd == 'init':
        config.update({
            'workspace_url': getattr(args, 'workspace_url', None),
            'root_url': getattr(args, 'root_url', None),  # Legacy support
        })
    elif args.cmd == 'push':
        config.update({
            'force_all': getattr(args, 'force_all', False),
            'dry_run': getattr(args, 'dry_run', False),
        })
    elif args.cmd == 'pull':
        config.update({
            'new_only': getattr(args, 'new_only', False),
            'existing_only': getattr(args, 'existing_only', False),
            'dry_run': getattr(args, 'dry_run', False),
        })
    elif args.cmd == 'clone':
        config.update({
            'notion_url': getattr(args, 'notion_url', None),
            'local_folder': getattr(args, 'local_folder', None),
            'workspace_url': getattr(args, 'workspace_url', None),
        })
    elif args.cmd == 'status':
        config.update({
            'fix': getattr(args, 'fix', False),
        })
    elif args.cmd == 'repo':
        config.update({
            'repo_command': getattr(args, 'repo_cmd', None),
            'name': getattr(args, 'name', None),
            'dir': getattr(args, 'dir', '.'),
            'root_page_url': getattr(args, 'root_page_url', None),
        })
    
    return config
