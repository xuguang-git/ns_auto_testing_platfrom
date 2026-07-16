export interface ModuleTreeItem {
  id: number;
  name: string;
  code?: string;
  parent?: number | null;
  platform?: string;
  managed_platform?: number | null;
  path_ids?: number[];
  path_names?: string[];
}

export interface ModuleTreeOption {
  value: number;
  label: string;
  children: ModuleTreeOption[];
}

export const modulePathNames = (modules: ModuleTreeItem[], moduleId?: number) => {
  const module = modules.find((item) => item.id === moduleId);
  if (!module) return [] as string[];
  if (module.path_names?.length) return module.path_names;
  const names: string[] = [];
  const visited = new Set<number>();
  let current: ModuleTreeItem | undefined = module;
  while (current && !visited.has(current.id)) {
    names.unshift(current.name);
    visited.add(current.id);
    current = modules.find((item) => item.id === current?.parent);
  }
  return names;
};

export const modulePathLabel = (modules: ModuleTreeItem[], moduleId?: number, fallback = "未分配") => {
  const names = modulePathNames(modules, moduleId);
  return names.length ? names.join(" / ") : fallback;
};

export const buildModuleTreeOptions = (modules: ModuleTreeItem[], platform?: string): ModuleTreeOption[] => {
  const scoped = modules.filter((item) => !platform || item.platform === platform);
  const childrenMap = scoped.reduce<Record<number, ModuleTreeItem[]>>((result, item) => {
    if (item.parent) (result[item.parent] ||= []).push(item);
    return result;
  }, {});
  const build = (item: ModuleTreeItem): ModuleTreeOption => ({
    value: item.id,
    label: modulePathLabel(modules, item.id, item.name),
    children: (childrenMap[item.id] || []).map(build),
  });
  return scoped.filter((item) => !item.parent).map(build);
};

export const collectModuleDescendantIds = (modules: ModuleTreeItem[], moduleId: number) => {
  const ids = new Set<number>([moduleId]);
  const pending = [moduleId];
  while (pending.length) {
    const parentId = pending.shift() as number;
    modules.filter((item) => item.parent === parentId).forEach((child) => {
      ids.add(child.id);
      pending.push(child.id);
    });
  }
  return [...ids];
};
