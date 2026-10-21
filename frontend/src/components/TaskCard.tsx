import React from 'react';
import { Task, TaskPriority, TaskStatus } from '../types';
import {
  Calendar,
  CheckCircle,
  Circle,
  Trash2,
  Edit2,
} from 'lucide-react';

interface TaskCardProps {
  task: Task;
  onToggleStatus: (task: Task) => void;
  onEdit: (task: Task) => void;
  onDelete: (taskId: string) => void;
}

export const TaskCard: React.FC<TaskCardProps> = ({
  task,
  onToggleStatus,
  onEdit,
  onDelete,
}) => {
  const isCompleted = task.status === 'completed';

  const priorityBadges: Record<TaskPriority, { text: string; bg: string; textCol: string }> = {
    low: { text: 'Low', bg: 'bg-slate-100', textCol: 'text-slate-700' },
    medium: { text: 'Medium', bg: 'bg-blue-50', textCol: 'text-blue-700' },
    high: { text: 'High', bg: 'bg-red-50', textCol: 'text-red-700' },
  };

  const statusBadges: Record<TaskStatus, { text: string; bg: string; textCol: string }> = {
    pending: { text: 'Pending', bg: 'bg-amber-50', textCol: 'text-amber-700' },
    in_progress: { text: 'In Progress', bg: 'bg-indigo-50', textCol: 'text-indigo-700' },
    completed: { text: 'Completed', bg: 'bg-emerald-50', textCol: 'text-emerald-700' },
  };

  const isOverdue =
    task.due_date &&
    new Date(task.due_date) < new Date() &&
    task.status !== 'completed';

  return (
    <div
      className={`bg-white rounded-xl border p-5 shadow-sm transition hover:shadow-md ${
        isCompleted ? 'border-slate-200 opacity-75' : 'border-slate-200'
      }`}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-start space-x-3 flex-1">
          <button
            onClick={() => onToggleStatus(task)}
            className="mt-0.5 text-slate-400 hover:text-emerald-600 transition"
          >
            {isCompleted ? (
              <CheckCircle className="w-5 h-5 text-emerald-600 fill-emerald-100" />
            ) : (
              <Circle className="w-5 h-5" />
            )}
          </button>
          <div className="flex-1">
            <h4
              className={`text-base font-semibold ${
                isCompleted ? 'line-through text-slate-400' : 'text-slate-900'
              }`}
            >
              {task.title}
            </h4>
            {task.description && (
              <p className="text-sm text-slate-600 mt-1 line-clamp-2">{task.description}</p>
            )}

            <div className="flex flex-wrap items-center gap-2 mt-3 text-xs">
              {/* Priority Badge */}
              <span
                className={`px-2 py-0.5 rounded-md font-medium ${priorityBadges[task.priority].bg} ${
                  priorityBadges[task.priority].textCol
                }`}
              >
                {priorityBadges[task.priority].text}
              </span>

              {/* Status Badge */}
              <span
                className={`px-2 py-0.5 rounded-md font-medium ${statusBadges[task.status].bg} ${
                  statusBadges[task.status].textCol
                }`}
              >
                {statusBadges[task.status].text}
              </span>

              {/* Due Date Indicator */}
              {task.due_date && (
                <span
                  className={`flex items-center space-x-1 px-2 py-0.5 rounded-md ${
                    isOverdue ? 'bg-red-50 text-red-700 font-semibold' : 'text-slate-500'
                  }`}
                >
                  <Calendar className="w-3.5 h-3.5 mr-1" />
                  <span>
                    {new Date(task.due_date).toLocaleDateString(undefined, {
                      month: 'short',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </span>
                  {isOverdue && <span className="ml-1 text-[10px] uppercase font-bold">(Overdue)</span>}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center space-x-1 ml-4">
          <button
            onClick={() => onEdit(task)}
            className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition"
            title="Edit task"
          >
            <Edit2 className="w-4 h-4" />
          </button>
          <button
            onClick={() => onDelete(task.id)}
            className="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition"
            title="Delete task"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};
